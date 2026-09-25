C     Image preparation done before ELLIPROF, reproducing the MONSTA
C     commands the SBF pipeline ran on the image buffer:
C
C        --sky V        SC 1 V      A = A + (-V)      (arith.f ARITHCON)
C        --sky-image F  RD 2 F; SI 1 2   A = A - B    (arith2im.f)
C        --mask F       RD 2 F; MI 1 2   A = A * B    (arith2im.f)
C
C     All arithmetic is REAL*4, element by element, as in MONSTA.  The
C     sky must be removed before the mask so that masked pixels end up
C     exactly 0, which is what ELLIPROF treats as missing data.
C     Unlike MONSTA's SI/MI, which silently work on the overlap of two
C     images, the second image must have the same size and origin.

C     Parse a number the way VISTA parses "SC 1 value": DISSECT, then a
C     float via CONST (REAL*4) or an integer via FLOAT(IBUF).
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
      IERR = 0
      RETURN
      END

C     SC 1 V
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

C     RD 2 F; SI 1 2.  The sky image goes through the same CFITSIO
C     reader as the science image.
      SUBROUTINE SUBSKYIMG(FNAME, PIX, NCOL, NROW, ISC, ISR, IERR)
      CHARACTER*(*) FNAME
      INTEGER NCOL, NROW, ISC, ISR, IERR
      REAL PIX(NCOL,NROW)
      REAL, ALLOCATABLE :: B(:,:)
      INTEGER IUNIT, BCOL, BROW, BSC, BSR, I, J
      CHARACTER*81840 HTMP

      CALL FITSOPENIM(FNAME, IUNIT, BCOL, BROW, BSC, BSR, HTMP, IERR)
      IF (IERR .NE. 0) RETURN
      CALL CHKGEOM('sky image', FNAME, BCOL, BROW, BSC, BSR,
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

C     RD 2 F; MI 1 2.  Returns the mask BITPIX, the number of zero
C     (masked) pixels and of values other than 0 or 1.
      SUBROUTINE APPLYMASK(FNAME, PIX, NCOL, NROW, ISC, ISR,
     $     MBITPIX, NZERO, NOTHER, IERR)
      CHARACTER*(*) FNAME
      INTEGER NCOL, NROW, ISC, ISR, MBITPIX, NZERO, NOTHER, IERR
      REAL PIX(NCOL,NROW)
      REAL, ALLOCATABLE :: M(:,:)
      INTEGER MCOL, MROW, MSC, MSR, IOFF, I, J

      CALL MASKHEAD(FNAME, MBITPIX, MCOL, MROW, MSC, MSR, IOFF, IERR)
      IF (IERR .NE. 0) RETURN
      CALL CHKGEOM('mask', FNAME, MCOL, MROW, MSC, MSR,
     $     NCOL, NROW, ISC, ISR, IERR)
      IF (IERR .NE. 0) RETURN
      ALLOCATE (M(NCOL,NROW))
      CALL MASKREAD(FNAME, MBITPIX, IOFF, NCOL, NROW, M, IERR)
      IF (IERR .EQ. 0) THEN
         NZERO = 0
         NOTHER = 0
         DO 10 J = 1, NROW
            DO 11 I = 1, NCOL
               IF (M(I,J) .EQ. 0.0) THEN
                  NZERO = NZERO + 1
               ELSE IF (M(I,J) .NE. 1.0) THEN
                  NOTHER = NOTHER + 1
               END IF
               PIX(I,J) = PIX(I,J) * M(I,J)
 11         CONTINUE
 10      CONTINUE
      END IF
      DEALLOCATE (M)
      RETURN
      END

C     The second image must match the science image exactly.
      SUBROUTINE CHKGEOM(WHAT, FNAME, BCOL, BROW, BSC, BSR,
     $     NCOL, NROW, ISC, ISR, IERR)
      CHARACTER*(*) WHAT, FNAME
      INTEGER BCOL, BROW, BSC, BSR, NCOL, NROW, ISC, ISR, IERR
      IERR = 0
      IF (BCOL .NE. NCOL .OR. BROW .NE. NROW) THEN
         WRITE (0,1000) WHAT, FNAME(1:LEN_TRIM(FNAME)), BCOL, BROW,
     $        NCOL, NROW
 1000    FORMAT (' elliprof: ',A,' ',A,' is ',I0,' x ',I0,
     $        ' pixels but the image is ',I0,' x ',I0)
         IERR = 1
      ELSE IF (BSC .NE. ISC .OR. BSR .NE. ISR) THEN
         WRITE (0,1001) WHAT, FNAME(1:LEN_TRIM(FNAME)), BSC, BSR,
     $        ISC, ISR
 1001    FORMAT (' elliprof: ',A,' ',A,
     $        ' has origin (CNPIX1,CNPIX2) = (',I0,',',I0,
     $        ') but the image has (',I0,',',I0,')')
         IERR = 1
      END IF
      RETURN
      END
