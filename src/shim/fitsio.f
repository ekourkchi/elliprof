C     FITS image input/output through the CFITSIO Fortran interface.
C     Reads the science image and writes model/diagnostic images.

C     Open an image, return its size, the image origin and the header
C     cards.  As in the original environment, the origin is
C     ISC = CNPIX1, ISR = CNPIX2, or 0 when those keywords are absent.
      SUBROUTINE FITSOPENIM(FNAME, IUNIT, NCOL, NROW, ISC, ISR,
     $     HEAD, IERR)
      CHARACTER*(*) FNAME, HEAD
      INTEGER IUNIT, NCOL, NROW, ISC, ISR, IERR
      INTEGER STATUS, NAXIS, NAXES(3), NKEYS, NMORE, I, NCARD
      INTEGER HDUTYP
      CHARACTER*80 CARD, COMMENT

      IERR = 1
      STATUS = 0
      CALL FTGIOU(IUNIT, STATUS)
C     FTNOPN (not FTOPEN, which always returns to the primary HDU)
C     honours an HDU selector: file.fits[N], file.fits[EXTNAME]
      CALL FTNOPN(IUNIT, FNAME, 0, STATUS)
      IF (STATUS .NE. 0) THEN
         CALL FITSERR('cannot open '//FNAME(1:LEN_TRIM(FNAME)), STATUS)
         RETURN
      END IF

C     The HDU CFITSIO selected (the primary one, or file.fits[N] /
C     file.fits[EXTNAME]) must itself be an image: never fall back to
C     another HDU.
      CALL FTGHDT(IUNIT, HDUTYP, STATUS)
      IF (STATUS .EQ. 0 .AND. HDUTYP .NE. 0) THEN
         WRITE (0,'(3A)') 'elliprof: error: ', FNAME(1:LEN_TRIM(FNAME)),
     $        ': the selected HDU is a table, not an image'
         CALL FITSCLOSE(IUNIT)
         RETURN
      END IF
      NAXIS = 0
      CALL FTGIDM(IUNIT, NAXIS, STATUS)
      IF (STATUS .NE. 0 .OR. NAXIS .LT. 2) THEN
         WRITE (0,'(3A,I0,2A)') 'elliprof: error: ',
     $        FNAME(1:LEN_TRIM(FNAME)),
     $        ': the selected HDU has no 2-D image (NAXIS = ', NAXIS,
     $        '); for an image in an extension use "file.fits[1]"',
     $        ' or "file.fits[EXTNAME]"'
         CALL FITSCLOSE(IUNIT)
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

C     Mask pixels as REAL*4, with CFITSIO's undefined pixels (BLANK in
C     integer images, NaN in floating-point ones) flagged; then close.
      SUBROUTINE FITSREADFLAG(IUNIT, NPIX, PIX, UNDEF, IERR)
      INTEGER IUNIT, NPIX, IERR
      REAL PIX(NPIX)
      LOGICAL UNDEF(NPIX), ANYNUL
      INTEGER STATUS

      STATUS = 0
      CALL FTGPFE(IUNIT, 1, 1, NPIX, PIX, UNDEF, ANYNUL, STATUS)
      IF (STATUS .NE. 0) CALL FITSERR('reading pixels', STATUS)
      IERR = STATUS
      CALL FITSCLOSE(IUNIT)
      RETURN
      END

C     Write a generated REAL*4 image (MODEL, PREPARED or RESIDUAL) to
C     FNAME, replacing any existing file.  Its header is that of the
C     science image TMPL -- the HDU the fit used, e.g. file.fits[SCI]:
C     CFITSIO writes the structural cards of the float image, then every
C     other card of the science header is copied in order, so the WCS
C     (CTYPE, CUNIT, CRPIX, CRVAL, CD, PC, CDELT, CROTA, PV, SIP,
C     alternate WCS, RADESYS, EQUINOX, ...), BUNIT, CNPIX and the rest
C     are kept exactly.  Left out are the cards that describe how the
C     science data are stored (see SKIPKEY).  HISTORY names the product.
      SUBROUTINE FITSWRITEPROD(FNAME, TMPL, NCOL, NROW, PIX, PRODUCT,
     $     IERR)
      CHARACTER*(*) FNAME, TMPL, PRODUCT
      INTEGER NCOL, NROW, IERR
      REAL PIX(NCOL,NROW)
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
C     A tile-compressed science image: its header also holds the cards
C     of the compression table, which must not be copied
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
      CALL FTPHPS(IUNIT, -32, 2, NAXES, STATUS)
      NSKIP = 0
      DO 20 I = 1, NKEYS
         IF (STATUS .NE. 0) GOTO 30
         CALL FTGREC(TUNIT, I, CARD, STATUS)
         IF (CARD .EQ. ' ') GOTO 20
         IF (SKIPKEY(CARD(1:8), CMPRSD)) GOTO 20
         CALL FTPREC(IUNIT, CARD, STATUS)
         IF (STATUS .NE. 0) THEN
C           a card CFITSIO refuses to write (malformed): leave it out
            STATUS = 0
            CALL FTCMSG
            NSKIP = NSKIP + 1
         END IF
 20   CONTINUE
 30   IF (NSKIP .GT. 0) WRITE (0,'(A,I0,A)') 'elliprof: ', NSKIP,
     $     ' malformed header card(s) of the science image not copied'
      CALL FTPHIS(IUNIT, 'elliprof '//VERSTR//' product: '//PRODUCT,
     $     STATUS)
      CALL FTPPRE(IUNIT, 1, 1, NCOL*NROW, PIX, STATUS)
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

C     Header keyword KEY describes how the science data are stored, not
C     the image on the sky, so a generated product must not inherit it:
C     the structural cards (CFITSIO writes the product's own), scaling
C     and undefined-value cards (the product is REAL*4), checksums and
C     data ranges (the data differ), the extension names, and, for a
C     tile-compressed science image (CMPRSD), its compression-table cards.
      LOGICAL FUNCTION SKIPKEY(KEY, CMPRSD)
      CHARACTER*8 KEY
      LOGICAL CMPRSD, NUMBERED
      CHARACTER*8 STRUCT(20), CMP(20)
      INTEGER I
      DATA STRUCT /'SIMPLE', 'XTENSION', 'BITPIX', 'NAXIS', 'EXTEND',
     $     'PCOUNT', 'GCOUNT', 'GROUPS', 'BSCALE', 'BZERO', 'BLANK',
     $     'CHECKSUM', 'DATASUM', 'DATAMIN', 'DATAMAX', 'EXTNAME',
     $     'EXTVER', 'EXTLEVEL', 'INHERIT', 'END'/
      DATA CMP /'ZIMAGE', 'ZCMPTYPE', 'ZBITPIX', 'ZNAXIS', 'ZSIMPLE',
     $     'ZTENSION', 'ZEXTEND', 'ZBLOCKED', 'ZPCOUNT', 'ZGCOUNT',
     $     'ZHECKSUM', 'ZDATASUM', 'ZQUANTIZ', 'ZDITHER0', 'ZBLANK',
     $     'ZSCALE', 'ZZERO', 'ZMASKCMP', 'TFIELDS', 'THEAP'/
      SKIPKEY = .TRUE.
      DO 10 I = 1, 20
         IF (KEY .EQ. STRUCT(I)) RETURN
 10   CONTINUE
      IF (NUMBERED(KEY, 'NAXIS')) RETURN
      IF (CMPRSD) THEN
         DO 20 I = 1, 20
            IF (KEY .EQ. CMP(I)) RETURN
 20      CONTINUE
         IF (NUMBERED(KEY, 'ZNAXIS') .OR. NUMBERED(KEY, 'ZTILE') .OR.
     $        NUMBERED(KEY, 'ZNAME') .OR. NUMBERED(KEY, 'ZVAL') .OR.
     $        NUMBERED(KEY, 'TTYPE') .OR. NUMBERED(KEY, 'TFORM') .OR.
     $        NUMBERED(KEY, 'TUNIT') .OR. NUMBERED(KEY, 'TDIM') .OR.
     $        NUMBERED(KEY, 'TNULL') .OR. NUMBERED(KEY, 'TSCAL') .OR.
     $        NUMBERED(KEY, 'TZERO')) RETURN
      END IF
      SKIPKEY = .FALSE.
      RETURN
      END

C     KEY is ROOT followed by digits only (e.g. NAXIS2, TTYPE12).
      LOGICAL FUNCTION NUMBERED(KEY, ROOT)
      CHARACTER*(*) KEY, ROOT
      INTEGER L, I, LK
      NUMBERED = .FALSE.
      L = LEN(ROOT)
      LK = LEN_TRIM(KEY)
      IF (LK .LE. L) RETURN
      IF (KEY(1:L) .NE. ROOT) RETURN
      DO 10 I = L+1, LK
         IF (KEY(I:I) .LT. '0' .OR. KEY(I:I) .GT. '9') RETURN
 10   CONTINUE
      NUMBERED = .TRUE.
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
