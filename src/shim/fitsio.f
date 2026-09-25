C     FITS image input/output through the CFITSIO Fortran interface.
C     Reads the science image and writes model/diagnostic images.

C     Open an image, return its size, the image origin and the header
C     cards.  As in the original environment, the origin is
C     ISC = CNPIX1, ISR = CNPIX2, or 0 when those keywords are absent.
      SUBROUTINE FITSOPENIM(FNAME, IUNIT, NCOL, NROW, ISC, ISR,
     $     HEAD, IERR)
      CHARACTER*(*) FNAME, HEAD
      INTEGER IUNIT, NCOL, NROW, ISC, ISR, IERR
      INTEGER STATUS, BLOCK, NAXIS, NAXES(3), NKEYS, NMORE, I, NCARD
      CHARACTER*80 CARD, COMMENT

      IERR = 1
      STATUS = 0
      CALL FTGIOU(IUNIT, STATUS)
      CALL FTOPEN(IUNIT, FNAME, 0, BLOCK, STATUS)
      IF (STATUS .NE. 0) THEN
         CALL FITSERR('cannot open '//FNAME(1:LEN_TRIM(FNAME)), STATUS)
         RETURN
      END IF

      CALL FTGIDM(IUNIT, NAXIS, STATUS)
      IF (STATUS .NE. 0 .OR. NAXIS .LT. 2) THEN
         WRITE (0,*) 'elliprof: ', FNAME(1:LEN_TRIM(FNAME)),
     $        ' has no 2-D image in this HDU (NAXIS =', NAXIS,
     $        '); for an extension use file.fits[1]'
         RETURN
      END IF
      NAXES(3) = 1
      CALL FTGISZ(IUNIT, MIN(NAXIS,3), NAXES, STATUS)
      NCOL = NAXES(1)
      NROW = NAXES(2)
      IF (NAXIS .GT. 2 .AND. NAXES(3) .GT. 1) WRITE (0,*)
     $     'elliprof: NAXIS =', NAXIS, '; using the first plane only'

      CALL FTGKYJ(IUNIT, 'CNPIX1', ISC, COMMENT, STATUS)
      IF (STATUS .EQ. 202) THEN
         ISC = 0
         STATUS = 0
         CALL FTCMSG
      END IF
      CALL FTGKYJ(IUNIT, 'CNPIX2', ISR, COMMENT, STATUS)
      IF (STATUS .EQ. 202) THEN
         ISR = 0
         STATUS = 0
         CALL FTCMSG
      END IF

      HEAD = ' '
      CALL FTGHSP(IUNIT, NKEYS, NMORE, STATUS)
      NCARD = MIN(NKEYS, LEN(HEAD)/80 - 1)
      DO 10 I = 1, NCARD
         CALL FTGREC(IUNIT, I, CARD, STATUS)
         HEAD((I-1)*80+1:I*80) = CARD
 10   CONTINUE
      HEAD(NCARD*80+1:NCARD*80+3) = 'END'

      IF (STATUS .NE. 0) THEN
         CALL FITSERR('reading header of '//FNAME(1:LEN_TRIM(FNAME)),
     $        STATUS)
         RETURN
      END IF
      IERR = 0
      RETURN
      END

C     Read the pixels as REAL*4 (BSCALE/BZERO applied, no NULL
C     substitution, as the original reader), then close the file.
      SUBROUTINE FITSREADPIX(IUNIT, NCOL, NROW, PIX, IERR)
      INTEGER IUNIT, NCOL, NROW, IERR
      REAL PIX(NCOL,NROW), NULVAL
      INTEGER STATUS
      LOGICAL ANYNUL

      STATUS = 0
      NULVAL = 0.0
      CALL FTGPVE(IUNIT, 1, 1, NCOL*NROW, NULVAL, PIX, ANYNUL, STATUS)
      IF (STATUS .NE. 0) CALL FITSERR('reading pixels', STATUS)
      IERR = STATUS
      STATUS = 0
      CALL FTCLOS(IUNIT, STATUS)
      CALL FTFIOU(IUNIT, STATUS)
      RETURN
      END

C     Close a file left open by FITSOPENIM without reading it.
      SUBROUTINE FITSCLOSE(IUNIT)
      INTEGER IUNIT, STATUS
      STATUS = 0
      CALL FTCLOS(IUNIT, STATUS)
      CALL FTFIOU(IUNIT, STATUS)
      RETURN
      END

C     CFITSIO library version, for --version.
      SUBROUTINE FITSLIBVER(VERSION)
      REAL VERSION
      CALL FTVERS(VERSION)
      RETURN
      END

C     Write a REAL*4 image, replacing any existing file.
      SUBROUTINE FITSWRITEIM(FNAME, NCOL, NROW, PIX, ISC, ISR, HIST,
     $     IERR)
      CHARACTER*(*) FNAME, HIST
      INTEGER NCOL, NROW, ISC, ISR, IERR
      REAL PIX(NCOL,NROW)
      INTEGER STATUS, IUNIT, NAXES(2)

      STATUS = 0
      CALL FTGIOU(IUNIT, STATUS)
      CALL FTINIT(IUNIT, '!'//FNAME(1:LEN_TRIM(FNAME)), 1, STATUS)
      NAXES(1) = NCOL
      NAXES(2) = NROW
      CALL FTPHPS(IUNIT, -32, 2, NAXES, STATUS)
      IF (ISC .NE. 0 .OR. ISR .NE. 0) THEN
         CALL FTPKYJ(IUNIT, 'CNPIX1', ISC, 'Start column', STATUS)
         CALL FTPKYJ(IUNIT, 'CNPIX2', ISR, 'Start row', STATUS)
      END IF
      CALL FTPHIS(IUNIT, HIST, STATUS)
      CALL FTPPRE(IUNIT, 1, 1, NCOL*NROW, PIX, STATUS)
      CALL FTCLOS(IUNIT, STATUS)
      CALL FTFIOU(IUNIT, STATUS)
      IF (STATUS .NE. 0) CALL FITSERR('writing '//
     $     FNAME(1:LEN_TRIM(FNAME)), STATUS)
      IERR = STATUS
      RETURN
      END

      SUBROUTINE FITSERR(WHAT, STATUS)
      CHARACTER*(*) WHAT
      INTEGER STATUS
      CHARACTER*30 TEXT
      CALL FTGERR(STATUS, TEXT)
      WRITE (0,*) 'elliprof: ', WHAT, ': CFITSIO status', STATUS,
     $     ' (', TEXT(1:LEN_TRIM(TEXT)), ')'
      RETURN
      END
