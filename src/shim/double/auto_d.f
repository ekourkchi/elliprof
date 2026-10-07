C     --precision auto: choose the backend from the data.
C
C     Double precision is chosen when the single backend could not hold
C     the data:
C       (A) the science image is stored with BITPIX 64 or -64;
C       (B) the sky image (--sky-image) is stored with BITPIX 64 or -64;
C       (C) a finite science or sky-image value, after BSCALE/BZERO,
C           would be Inf in float32 or is nonzero but would be 0 in
C           float32 (checked on the actual values, read in double, and
C           only when BSCALE/BZERO make that possible: unscaled 8-, 16-
C           and 32-bit integers and 32-bit floats never do);
C       (D) the --sky value, or SKY=, meets the same criterion, or is a
C           valid finite number that the historical single parser
C           (DISSECT, through PARSENUM) cannot read: it is run on the
C           text, so its actual behaviour decides (AUTOSCAL).
C     Not for values that stay nonzero float32 subnormals, values that
C     merely are not exact in float32, or 32-bit integers above 2**24.
C     Masks are never considered.  Otherwise single.  WHY explains the
C     choice.  Nothing here changes how the single backend then reads
C     the data.
      SUBROUTINE AUTOPREC(FITSFILE, SKYIMG, SKYSTR, PRECSEL, WHY, IERR)
      CHARACTER*(*) FITSFILE, SKYIMG, SKYSTR, PRECSEL, WHY
      INTEGER IERR
      INCLUDE 'vistalink.inc'
      DOUBLE PRECISION V
      INTEGER I, IBP, NOVER, NZERO, IWHY
      LOGICAL F32BAD

      PRECSEL = 'double'
      IERR = 0
      CALL AUTOIMG(FITSFILE, IBP, NOVER, NZERO, IERR)
      IF (IERR .NE. 0) RETURN
      IF (IBP .EQ. 64 .OR. IBP .EQ. -64) THEN
         WRITE (WHY,'(A,I0,A)') ' (auto: science image BITPIX ', IBP,
     $        ')'
         RETURN
      END IF
      IF (NOVER + NZERO .GT. 0) THEN
         CALL AUTOWHY('science image', NOVER, NZERO, WHY)
         RETURN
      END IF
      IF (SKYIMG .NE. ' ') THEN
         CALL AUTOIMG(SKYIMG, IBP, NOVER, NZERO, IERR)
         IF (IERR .NE. 0) RETURN
         IF (IBP .EQ. 64 .OR. IBP .EQ. -64) THEN
            WRITE (WHY,'(A,I0,A)') ' (auto: sky image BITPIX ', IBP,
     $           ')'
            RETURN
         END IF
         IF (NOVER + NZERO .GT. 0) THEN
            CALL AUTOWHY('sky image', NOVER, NZERO, WHY)
            RETURN
         END IF
      END IF
      IF (SKYSTR .NE. ' ') THEN
         CALL AUTOSCAL(SKYSTR, IWHY)
         IF (IWHY .EQ. 1) THEN
            WHY = ' (auto: the --sky value is beyond float32)'
            RETURN
         ELSE IF (IWHY .EQ. 2) THEN
            WHY = ' (auto: the --sky value cannot be read by the '
     $           //'single parser)'
            RETURN
         END IF
      END IF
      DO 10 I = 1, NCON
         IF (WORD(I)(1:4) .EQ. 'SKY=') THEN
            CALL AUTOSCAL(WORD(I)(5:), IWHY)
            IF (IWHY .EQ. 1) THEN
               WHY = ' (auto: SKY= is beyond float32)'
               RETURN
            ELSE IF (IWHY .EQ. 2) THEN
               WHY = ' (auto: SKY= cannot be read by the single parser)'
               RETURN
            END IF
         END IF
 10   CONTINUE
      PRECSEL = 'single'
      WHY = ' (auto: every value is within float32)'
      RETURN
      END

C     The reason for (C).
      SUBROUTINE AUTOWHY(WHAT, NOVER, NZERO, WHY)
      CHARACTER*(*) WHAT, WHY
      INTEGER NOVER, NZERO
      IF (NOVER .GT. 0) THEN
         WRITE (WHY,'(3A,I0,A)') ' (auto: ', WHAT, ' has ', NOVER,
     $        ' value(s) beyond the float32 range)'
      ELSE
         WRITE (WHY,'(3A,I0,A)') ' (auto: ', WHAT, ' has ', NZERO,
     $        ' nonzero value(s) that are 0 in float32)'
      END IF
      RETURN
      END

C     True if the double V, converted to float32 (round to nearest),
C     would be Inf (V finite) or 0 (V nonzero).
      LOGICAL FUNCTION F32BAD(V)
      DOUBLE PRECISION V
      REAL R
      LOGICAL FINITED
      F32BAD = .FALSE.
      IF (.NOT. FINITED(V) .OR. V .EQ. 0) RETURN
      R = REAL(V)
      F32BAD = ABS(R) .GT. HUGE(R) .OR. R .EQ. 0
      RETURN
      END

C     BITPIX of image FNAME and, when BSCALE/BZERO could carry its
C     values beyond float32, how many finite values would be Inf
C     (NOVER) or 0 (NZERO) in float32.
      SUBROUTINE AUTOIMG(FNAME, IBP, NOVER, NZERO, IERR)
      CHARACTER*(*) FNAME
      INTEGER IBP, NOVER, NZERO, IERR
      DOUBLE PRECISION, ALLOCATABLE :: B(:)
      DOUBLE PRECISION BSCALE, BZERO
      INTEGER IUNIT, NCOL, NROW, ISC, ISR, STATUS, IST
      INTEGER*8 I, NPIX
      CHARACTER*80 COMMENT
      CHARACTER*81840 HTMP
      LOGICAL F32BAD

      NOVER = 0
      NZERO = 0
      CALL FITSOPENIM(FNAME, IUNIT, NCOL, NROW, ISC, ISR, HTMP, IERR)
      IF (IERR .NE. 0) RETURN
      CALL FITSBITPIX(IUNIT, IBP)
      STATUS = 0
      CALL FTGKYD(IUNIT, 'BSCALE', BSCALE, COMMENT, STATUS)
      IF (STATUS .NE. 0) BSCALE = 1
      STATUS = 0
      CALL FTGKYD(IUNIT, 'BZERO', BZERO, COMMENT, STATUS)
      IF (STATUS .NE. 0) BZERO = 0
      STATUS = 0
      CALL FTCMSG
      IF (IBP .EQ. 64 .OR. IBP .EQ. -64 .OR.
     $     (BSCALE .EQ. 1 .AND. BZERO .EQ. 0) .OR.
     $     (IBP .GT. 0 .AND. BSCALE .EQ. 1 .AND.
     $     ABS(BZERO) .LE. 2D0**32)) THEN
         CALL FITSCLOSE(IUNIT)
         RETURN
      END IF
      NPIX = INT(NCOL,8) * NROW
      ALLOCATE (B(NPIX), STAT=IST)
      IF (IST .NE. 0) THEN
         CALL FITSCLOSE(IUNIT)
         CALL NOMEMD('the image for --precision auto', 8D0*NPIX)
         IERR = 2
         RETURN
      END IF
      CALL FITSREADPIXD(IUNIT, NCOL, NROW, B, IERR)
      IF (IERR .EQ. 0) THEN
         DO 10 I = 1, NPIX
            IF (F32BAD(B(I))) THEN
               IF (ABS(B(I)) .GE. 1) THEN
                  NOVER = NOVER + 1
               ELSE
                  NZERO = NZERO + 1
               END IF
            END IF
 10      CONTINUE
      END IF
      DEALLOCATE (B)
      RETURN
      END

C     A scalar (--sky or SKY=) for --precision auto.  IWHY = 0: single
C     can take it; 1: a plain number whose float32 value would be Inf,
C     or 0 although it is nonzero (or beyond double itself: the double
C     driver then reports that); 2: a valid finite number that the
C     historical single parser (PARSENUM -> DISSECT) refuses, or reads
C     as 0 or a non-finite value.  Not a plain number at all (e.g. an
C     expression for SKY=): 0, the single path then handles it as before.
      SUBROUTINE AUTOSCAL(STR, IWHY)
      CHARACTER*(*) STR
      INTEGER IWHY, J, JS
      DOUBLE PRECISION V
      REAL SV
      LOGICAL F32BAD
      IWHY = 0
      CALL PARSENUMD(STR, V, J)
      IF (J .EQ. 1) RETURN
      IF (J .EQ. 2 .OR. J .EQ. 3 .OR. F32BAD(V)) THEN
         IWHY = 1
         RETURN
      END IF
      CALL PARSENUM(STR, SV, JS)
      IF (JS .NE. 0) THEN
         IWHY = 2
      ELSE IF (V .NE. 0 .AND. SV .EQ. 0) THEN
         IWHY = 2
      END IF
      RETURN
      END
