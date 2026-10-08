C     FITS input/output of the double backend (see fitsio.f for the
C     single one, whose FITSOPENIM, SKIPKEY and FITSERR are shared).

C     Read the pixels as REAL*8 (FTGPVD: CFITSIO applies BSCALE/BZERO in
C     double; no NULL substitution, as FITSREADPIX), then close.
      SUBROUTINE FITSREADPIXD(IUNIT, NCOL, NROW, PIX, IERR)
      IMPLICIT NONE
      INTEGER IUNIT, NCOL, NROW, IERR
      DOUBLE PRECISION PIX(NCOL,NROW), NULVAL
      INTEGER STATUS
      LOGICAL ANYNUL

      STATUS = 0
      NULVAL = 0
      CALL FTGPVD(IUNIT, 1, 1, NCOL*NROW, NULVAL, PIX, ANYNUL, STATUS)
      IF (STATUS .NE. 0) CALL FITSERR('reading pixels', STATUS)
      IERR = STATUS
      STATUS = 0
      CALL FTCLOS(IUNIT, STATUS)
      CALL FTFIOU(IUNIT, STATUS)
      RETURN
      END

C     Write a generated REAL*8 image (BITPIX -64, FTPPRD) with the
C     header of the science image TMPL, exactly as FITSWRITEPROD does
C     for REAL*4 (same cards copied, same cards left out), then the
C     product HISTORY card and NHIST more HISTORY cards HIST.
      SUBROUTINE FITSWRITEPRODD(FNAME, TMPL, NCOL, NROW, PIX, PRODUCT,
     $     NHIST, HIST, IERR)
      IMPLICIT NONE
      CHARACTER*(*) FNAME, TMPL, PRODUCT, HIST(*)
      INTEGER NCOL, NROW, NHIST, IERR
      DOUBLE PRECISION PIX(NCOL,NROW)
      INCLUDE 'version.inc'
      INTEGER STATUS, IUNIT, TUNIT, NAXES(2), NKEYS, NMORE, I
      INTEGER NSKIP, CSTAT
      CHARACTER*80 CARD
      LOGICAL CMPRSD, SKIPKEY

      IERR = 1
      STATUS = 0
      CALL FTGIOU(TUNIT, STATUS)
      CALL FTNOPN(TUNIT, TMPL, 0, STATUS)
      CALL FTGHSP(TUNIT, NKEYS, NMORE, STATUS)
      IF (STATUS .NE. 0) THEN
         CALL FITSERR('reading the header of '//TMPL(1:LEN_TRIM(TMPL)),
     $        STATUS)
         RETURN
      END IF
      CMPRSD = .FALSE.
      DO 10 I = 1, NKEYS
         CALL FTGREC(TUNIT, I, CARD, STATUS)
         IF (CARD(1:8) .EQ. 'ZIMAGE' .AND.
     $        INDEX(CARD(10:30), 'T') .GT. 0) CMPRSD = .TRUE.
 10   CONTINUE

      CALL FTGIOU(IUNIT, STATUS)
      CALL FTINIT(IUNIT, '!'//FNAME(1:LEN_TRIM(FNAME)), 1, STATUS)
      NAXES(1) = NCOL
      NAXES(2) = NROW
      CALL FTPHPS(IUNIT, -64, 2, NAXES, STATUS)
      NSKIP = 0
      DO 20 I = 1, NKEYS
         IF (STATUS .NE. 0) GOTO 30
         CALL FTGREC(TUNIT, I, CARD, STATUS)
         IF (CARD .EQ. ' ') GOTO 20
         IF (SKIPKEY(CARD(1:8), CMPRSD)) GOTO 20
         CALL FTPREC(IUNIT, CARD, STATUS)
         IF (STATUS .NE. 0) THEN
            STATUS = 0
            CALL FTCMSG
            NSKIP = NSKIP + 1
         END IF
 20   CONTINUE
 30   IF (NSKIP .GT. 0) WRITE (0,'(A,I0,A)') 'elliprof: ', NSKIP,
     $     ' malformed header card(s) of the science image not copied'
      CALL FTPHIS(IUNIT, 'elliprof '//VERSTR//' product: '//PRODUCT,
     $     STATUS)
      DO 40 I = 1, NHIST
         CALL FTPHIS(IUNIT, HIST(I), STATUS)
 40   CONTINUE
      CALL FTPPRD(IUNIT, 1, 1, NCOL*NROW, PIX, STATUS)
      CALL FTCLOS(IUNIT, STATUS)
      CALL FTFIOU(IUNIT, STATUS)
      CSTAT = 0
      CALL FTCLOS(TUNIT, CSTAT)
      CALL FTFIOU(TUNIT, CSTAT)
      IF (STATUS .NE. 0) THEN
         CALL FITSERR('writing '//FNAME(1:LEN_TRIM(FNAME)), STATUS)
         RETURN
      END IF
      IERR = 0
      RETURN
      END
