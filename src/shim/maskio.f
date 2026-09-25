C     Mask input.  A mask is an image multiplied into the science
C     image, so masked pixels become 0 and ELLIPROF skips them.
C     Legacy masks (e.g. *.dmask) use a non-standard FITS BITPIX = 1
C     bitmap, which CFITSIO rejects, so it is decoded here exactly as
C     the original reader did (its routines bitfp_ and FITSorder):
C       - data start at the first 2880-byte block after END,
C         2*((NPIX+15)/16) bytes, bits packed continuously across rows
C       - each byte pair is swapped (swab), then pixel i (0-based) is
C         bit (i mod 8), low bit first, of byte i/8: set -> 1.0,
C         clear -> 0.0
C       - bitfp_ walks backwards from the last pixel and starts on the
C         final byte unshifted, so in a final partial byte the pixels
C         sit in the high bits (as fpbit_ writes them)
C     Other BITPIX values are read through CFITSIO, as for the science
C     image, and multiply the image by their actual values, like MI.

C     Header of a mask file: BITPIX, size, CNPIX origin (0 if absent),
C     byte offset of the data.  Parses the primary header directly,
C     since CFITSIO cannot open BITPIX = 1 files.
      SUBROUTINE MASKHEAD(FNAME, MBITPIX, MCOL, MROW, MSC, MSR, IOFF,
     $     IERR)
      CHARACTER*(*) FNAME
      INTEGER MBITPIX, MCOL, MROW, MSC, MSR, IOFF, IERR
      CHARACTER*80 CARD
      CHARACTER*8 KEY
      INTEGER K, IOS, NAXIS, NAX1, NAX2, NAX3

      IERR = 1
      MBITPIX = 0
      NAXIS = -1
      NAX1 = 0
      NAX2 = 0
      NAX3 = 1
      MSC = 0
      MSR = 0
      OPEN (8, FILE=FNAME, ACCESS='STREAM', FORM='UNFORMATTED',
     $     STATUS='OLD', ACTION='READ', IOSTAT=IOS)
      IF (IOS .NE. 0) THEN
         WRITE (0,*) 'elliprof: cannot open mask ',
     $        FNAME(1:LEN_TRIM(FNAME))
         RETURN
      END IF
      READ (8, POS=1, IOSTAT=IOS) CARD
      IF (IOS .NE. 0 .OR. CARD(1:9) .NE. 'SIMPLE  =') THEN
         WRITE (0,*) 'elliprof: mask ', FNAME(1:LEN_TRIM(FNAME)),
     $        ' is not a FITS file'
         CLOSE (8)
         RETURN
      END IF
      K = 1
 10   K = K + 1
      READ (8, POS=(K-1)*80+1, IOSTAT=IOS) CARD
      IF (IOS .NE. 0) THEN
         WRITE (0,*) 'elliprof: mask ', FNAME(1:LEN_TRIM(FNAME)),
     $        ' has no END card'
         CLOSE (8)
         RETURN
      END IF
      KEY = CARD(1:8)
      IF (KEY .EQ. 'END') GOTO 20
      IF (KEY .EQ. 'BITPIX') CALL CARDINT(CARD, MBITPIX)
      IF (KEY .EQ. 'NAXIS') CALL CARDINT(CARD, NAXIS)
      IF (KEY .EQ. 'NAXIS1') CALL CARDINT(CARD, NAX1)
      IF (KEY .EQ. 'NAXIS2') CALL CARDINT(CARD, NAX2)
      IF (KEY .EQ. 'NAXIS3') CALL CARDINT(CARD, NAX3)
      IF (KEY .EQ. 'CNPIX1') CALL CARDINT(CARD, MSC)
      IF (KEY .EQ. 'CNPIX2') CALL CARDINT(CARD, MSR)
      GOTO 10
 20   CLOSE (8)
      IOFF = ((K*80 + 2879)/2880) * 2880
      IF (NAXIS .LT. 2 .OR. NAX1 .LE. 0 .OR. NAX2 .LE. 0 .OR.
     $     (NAXIS .GT. 2 .AND. NAX3 .GT. 1)) THEN
         WRITE (0,*) 'elliprof: mask ', FNAME(1:LEN_TRIM(FNAME)),
     $        ' is not a single 2-D image (NAXIS =', NAXIS, ')'
         RETURN
      END IF
      MCOL = NAX1
      MROW = NAX2
      IERR = 0
      RETURN
      END

C     Integer value of a header card (the original reader used atoi
C     on column 11 onwards; a '/' ends list-directed input).
      SUBROUTINE CARDINT(CARD, IVAL)
      CHARACTER*(*) CARD
      INTEGER IVAL, IOS
      REAL RVAL
      READ (CARD(11:), *, IOSTAT=IOS) IVAL
      IF (IOS .NE. 0) THEN
         READ (CARD(11:), *, IOSTAT=IOS) RVAL
         IF (IOS .EQ. 0) IVAL = INT(RVAL)
      END IF
      RETURN
      END

C     Read the mask pixels as REAL*4, the values the original reader
C     would put in the
C     image buffer.  MCOL x MROW must come from MASKHEAD.
      SUBROUTINE MASKREAD(FNAME, MBITPIX, IOFF, MCOL, MROW, PIX, IERR)
      CHARACTER*(*) FNAME
      INTEGER MBITPIX, IOFF, MCOL, MROW, IERR
      REAL PIX(MCOL*MROW)
      INTEGER IUNIT, NC, NR, I1, I2
      CHARACTER*81840 HTMP

      IF (MBITPIX .EQ. 1) THEN
         CALL READBITMAP(FNAME, IOFF, MCOL*MROW, PIX, IERR)
      ELSE
         CALL FITSOPENIM(FNAME, IUNIT, NC, NR, I1, I2, HTMP, IERR)
         IF (IERR .NE. 0) RETURN
         IF (NC .NE. MCOL .OR. NR .NE. MROW) THEN
            WRITE (0,*) 'elliprof: CFITSIO and header disagree on ',
     $           'the mask size'
            IERR = 1
            RETURN
         END IF
         CALL FITSREADPIX(IUNIT, NC, NR, PIX, IERR)
      END IF
      RETURN
      END

C     BITPIX = 1 data -> 0.0/1.0, a transcription of the original
C     bitfp_ and FITSorder(1, ...).
      SUBROUTINE READBITMAP(FNAME, IOFF, NPIX, PIX, IERR)
      CHARACTER*(*) FNAME
      INTEGER IOFF, NPIX, IERR
      REAL PIX(NPIX)
      INTEGER*1, ALLOCATABLE :: BYTES(:)
      INTEGER*1 T
      INTEGER NB, J, I, IB, IOS

      IERR = 1
      NB = 2*((NPIX+15)/16)
      ALLOCATE (BYTES(NB))
      OPEN (8, FILE=FNAME, ACCESS='STREAM', FORM='UNFORMATTED',
     $     STATUS='OLD', ACTION='READ', IOSTAT=IOS)
      IF (IOS .EQ. 0) READ (8, POS=IOFF+1, IOSTAT=IOS) BYTES
      CLOSE (8)
      IF (IOS .NE. 0) THEN
         WRITE (0,*) 'elliprof: mask ', FNAME(1:LEN_TRIM(FNAME)),
     $        ' is too short for its BITPIX = 1 data (',NB,' bytes)'
         DEALLOCATE (BYTES)
         RETURN
      END IF

C     FITSorder(1, npix, data): swab() the 2*((npix+15)/16) bytes
      DO 10 J = 1, NB-1, 2
         T = BYTES(J)
         BYTES(J) = BYTES(J+1)
         BYTES(J+1) = T
 10   CONTINUE

C     bitfp_: i = npix-1 .. 0 (0-based), b is an unsigned char
      IB = 0
      IF (MOD(NPIX-1,8) .NE. 7) IB = IAND(INT(BYTES((NPIX-1)/8+1)),255)
      DO 20 I = NPIX-1, 0, -1
         IF (MOD(I,8) .EQ. 7) IB = IAND(INT(BYTES(I/8+1)),255)
         IF (IAND(IB,128) .NE. 0) THEN
            PIX(I+1) = 1.0
         ELSE
            PIX(I+1) = 0.0
         END IF
         IB = IAND(ISHFT(IB,1),255)
 20   CONTINUE
      DEALLOCATE (BYTES)
      IERR = 0
      RETURN
      END
