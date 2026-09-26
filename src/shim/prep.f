C     Image preparation before ELLIPROF:
C
C        --sky V        A = A + (-V)
C        --sky-image F  A = A - B
C        --mask F       A = 0 where the mask is bad, else unchanged
C
C     So the prepared image is  good(mask) x (science - sky).  The mask
C     is logical: good = finite nonzero, bad = 0, NaN, Inf or undefined
C     (maskio.f); its values are never used as weights.  All arithmetic
C     is REAL*4, element by element.  The sky is removed first, and bad
C     pixels then set to exactly 0, which ELLIPROF treats as missing.  A sky image or
C     mask must have exactly the size and origin of the science image;
C     it is never resized, cropped, shifted or resampled.

C     Parse one number with the original parser (DISSECT): a float via
C     its REAL*4 value, an integer via FLOAT.  Non-finite values fail.
      SUBROUTINE PARSENUM(STR, VAL, IERR)
      CHARACTER*(*) STR
      REAL VAL
      INTEGER IERR
      CHARACTER*289 WORK, OSTRNG
      LOGICAL ERR
      INTEGER NTYPE, NUM, NCHAR, L, UPPER
      REAL FNUM

      IERR = 1
      WORK = STR
      L = UPPER(WORK)
      CALL DISSECT(WORK, 1, .FALSE., NTYPE, NUM, FNUM, OSTRNG, NCHAR,
     $     ERR)
      IF (ERR .OR. NTYPE .EQ. 3) RETURN
      CALL DISSECT(WORK, 2, .FALSE., NTYPE, NUM, FNUM, OSTRNG, NCHAR,
     $     ERR)
      IF (.NOT. ERR) RETURN
      CALL DISSECT(WORK, 1, .FALSE., NTYPE, NUM, FNUM, OSTRNG, NCHAR,
     $     ERR)
      IF (NTYPE .EQ. 1) THEN
         VAL = FLOAT(NUM)
      ELSE
         VAL = FNUM
      END IF
      IF (VAL .NE. VAL .OR. ABS(VAL) .GT. HUGE(VAL)) RETURN
      IERR = 0
      RETURN
      END

C     --sky V
      SUBROUTINE SUBSKY(PIX, NCOL, NROW, SKY)
      INTEGER NCOL, NROW, I, J
      REAL PIX(NCOL,NROW), SKY, F
      F = -SKY
      DO 10 J = 1, NROW
         DO 11 I = 1, NCOL
            PIX(I,J) = PIX(I,J) + F
 11      CONTINUE
 10   CONTINUE
      RETURN
      END

C     Check a sky image's size and origin without reading its pixels.
      SUBROUTINE CHKSKYIMG(FNAME, NCOL, NROW, ISC, ISR, IERR)
      CHARACTER*(*) FNAME
      INTEGER NCOL, NROW, ISC, ISR, IERR
      INTEGER IUNIT, BCOL, BROW, BSC, BSR
      CHARACTER*81840 HTMP

      CALL FITSOPENIM(FNAME, IUNIT, BCOL, BROW, BSC, BSR, HTMP, IERR)
      IF (IERR .NE. 0) RETURN
      CALL FITSCLOSE(IUNIT)
      CALL CHKGEOM('sky image', BCOL, BROW, BSC, BSR,
     $     NCOL, NROW, ISC, ISR, IERR)
      RETURN
      END

C     Check a mask's size and origin without reading its pixels.
      SUBROUTINE CHKMASK(FNAME, NCOL, NROW, ISC, ISR, IERR)
      CHARACTER*(*) FNAME
      INTEGER NCOL, NROW, ISC, ISR, IERR
      INTEGER MCOL, MROW, MSC, MSR

      CALL MASKGEOM(FNAME, MCOL, MROW, MSC, MSR, IERR)
      IF (IERR .NE. 0) RETURN
      CALL CHKGEOM('mask', MCOL, MROW, MSC, MSR,
     $     NCOL, NROW, ISC, ISR, IERR)
      RETURN
      END

C     --sky-image F: subtract it pixel by pixel.
      SUBROUTINE SUBSKYIMG(FNAME, PIX, NCOL, NROW, ISC, ISR, IERR)
      CHARACTER*(*) FNAME
      INTEGER NCOL, NROW, ISC, ISR, IERR
      REAL PIX(NCOL,NROW)
      REAL, ALLOCATABLE :: B(:,:)
      INTEGER IUNIT, BCOL, BROW, BSC, BSR, I, J
      CHARACTER*81840 HTMP

      CALL FITSOPENIM(FNAME, IUNIT, BCOL, BROW, BSC, BSR, HTMP, IERR)
      IF (IERR .NE. 0) RETURN
      CALL CHKGEOM('sky image', BCOL, BROW, BSC, BSR,
     $     NCOL, NROW, ISC, ISR, IERR)
      IF (IERR .NE. 0) THEN
         CALL FITSCLOSE(IUNIT)
         RETURN
      END IF
      ALLOCATE (B(NCOL,NROW))
      CALL FITSREADPIX(IUNIT, NCOL, NROW, B, IERR)
      IF (IERR .EQ. 0) THEN
         DO 10 J = 1, NROW
            DO 11 I = 1, NCOL
               PIX(I,J) = PIX(I,J) - B(I,J)
 11         CONTINUE
 10      CONTINUE
      END IF
      DEALLOCATE (B)
      RETURN
      END

C     --mask F: set bad pixels to 0.  Returns the logical mask GOOD,
C     the mask BITPIX (1 = legacy bitmap), the number of bad pixels and,
C     of those, how many were NaN, Inf or undefined.
      SUBROUTINE APPLYMASK(FNAME, PIX, NCOL, NROW, ISC, ISR, GOOD,
     $     MBITPIX, NBAD, NNONF, IERR)
      CHARACTER*(*) FNAME
      INTEGER NCOL, NROW, ISC, ISR, MBITPIX, NBAD, NNONF, IERR
      REAL PIX(NCOL,NROW)
      LOGICAL GOOD(NCOL,NROW)
      INTEGER I, J

      CALL CHKMASK(FNAME, NCOL, NROW, ISC, ISR, IERR)
      IF (IERR .NE. 0) RETURN
      CALL MASKGOOD(FNAME, NCOL, NROW, GOOD, MBITPIX, NBAD, NNONF,
     $     IERR)
      IF (IERR .NE. 0) RETURN
      DO 10 J = 1, NROW
         DO 11 I = 1, NCOL
            IF (.NOT. GOOD(I,J)) PIX(I,J) = 0.0
 11      CONTINUE
 10   CONTINUE
      RETURN
      END

C     The second image must match the science image exactly.
      SUBROUTINE CHKGEOM(WHAT, BCOL, BROW, BSC, BSR,
     $     NCOL, NROW, ISC, ISR, IERR)
      CHARACTER*(*) WHAT
      INTEGER BCOL, BROW, BSC, BSR, NCOL, NROW, ISC, ISR, IERR
      IERR = 0
      IF (BCOL .NE. NCOL .OR. BROW .NE. NROW) THEN
         WRITE (0,1000) WHAT, BCOL, BROW, NCOL, NROW
 1000    FORMAT ('elliprof: error: ',A,' dimensions (',I0,' x ',I0,
     $        ') do not match science image dimensions (',I0,' x ',
     $        I0,')')
         IERR = 1
      ELSE IF (BSC .NE. ISC .OR. BSR .NE. ISR) THEN
         WRITE (0,1001) WHAT, BSC, BSR, ISC, ISR
 1001    FORMAT ('elliprof: error: ',A,' origin (CNPIX1,CNPIX2) = (',
     $        I0,',',I0,') does not match science image origin (',
     $        I0,',',I0,')')
         IERR = 1
      END IF
      RETURN
      END
