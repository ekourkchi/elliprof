C     The double-precision driver: what main.f does after the command
C     line, with every image and intensity in DOUBLE PRECISION
C     (IEEE-754 binary64), for ELLIPROFD (src/double).  main.f parses
C     and checks the command line for both backends and calls this
C     for --precision double; the single path never comes here.
C
C     Stages: read (FTGPVD) -> sky (double) -> mask -> prepared product
C     -> normalization (exact power of two) -> ELLIPROFD -> back to
C     physical units -> products.  ISTAT returns the exit status.

      SUBROUTINE ELLIPROFDRV(FITSFILE, PRFFILE, MODFILE, CSVFILE,
     $     REGFILE, MASKFILE, SKYIMG, SKYSTR, PREPFILE, RESFILE, ZGOOD,
     $     PREPONLY, DOMODEL, PRECREQ, PRECWHY, ISTAT)
      CHARACTER*(*) FITSFILE, PRFFILE, MODFILE, CSVFILE, REGFILE
      CHARACTER*(*) MASKFILE, SKYIMG, SKYSTR, PREPFILE, RESFILE
      CHARACTER*(*) PRECREQ, PRECWHY
      LOGICAL ZGOOD, PREPONLY, DOMODEL
      INTEGER ISTAT
      INCLUDE 'vistalink.inc'
      INCLUDE 'imagelink.inc'
      INCLUDE 'profile_d.inc'
      INCLUDE 'norm_d.inc'

      DOUBLE PRECISION, ALLOCATABLE :: PIX(:,:), PREP(:,:)
      LOGICAL, ALLOCATABLE :: GOOD(:,:)
      DOUBLE PRECISION SKYVAL, BYTES
      INTEGER NCOL, NROW, IUNIT, IERR, IBITPIX, MBITPIX, NBAD, NNONF
      INTEGER NOVER, IST, KPREF, KMIN, KMAX, I, NHIST
      INTEGER*8 NPIX, NUSED, NINEX
      LOGICAL LINEAR, SHVERB
      CHARACTER*1024 SKYDESC, MSKDESC
      CHARACTER*72 HIST(4)
      CHARACTER*3 YESNO
      CHARACTER*16 MIBD
      COMMON /SHIMOPT/ SHVERB

      ISTAT = 1
      LINEAR = .FALSE.
      DO 5 I = 1, NCON
         IF (WORD(I) .EQ. 'LINEAR') LINEAR = .TRUE.
 5    CONTINUE

C     ---- --sky: parsed exactly, in double
      IF (SKYSTR .NE. ' ') THEN
         CALL PARSENUMD(SKYSTR, SKYVAL, IERR)
         IF (IERR .NE. 0) THEN
            IF (IERR .EQ. 2 .OR. IERR .EQ. 3) THEN
               WRITE (0,'(3A)') 'elliprof: error (double precision, '
     $              //'sky): --sky ', SKYSTR(1:LEN_TRIM(SKYSTR)),
     $              ' is outside the range of double precision'
            ELSE
               WRITE (0,'(2A)') 'elliprof: error (double precision, '
     $              //'sky): --sky needs one finite number, got ',
     $              SKYSTR(1:LEN_TRIM(SKYSTR))
            END IF
            RETURN
         END IF
      END IF

C     ---- Read the science image into buffer 1, in double

      CALL FITSOPENIM(FITSFILE, IUNIT, NCOL, NROW, ISC, ISR,
     $     HEADBUF(1), IERR)
      IF (IERR .NE. 0) RETURN
      NPIX = INT(NCOL,8) * NROW
C     memory: the image, its prepared copy for --residual, the logical
C     mask, and the largest transient buffer (a double sky image, or
C     the mask read in double with its flags)
      BYTES = 8D0*NPIX
      IF (RESFILE .NE. ' ') BYTES = BYTES + 8D0*NPIX
      IF (MASKFILE .NE. ' ' .OR. RESFILE .NE. ' ')
     $     BYTES = BYTES + 4D0*NPIX
      IF (MASKFILE .NE. ' ') THEN
         BYTES = BYTES + 12D0*NPIX
      ELSE IF (SKYIMG .NE. ' ') THEN
         BYTES = BYTES + 8D0*NPIX
      END IF
      IF (SHVERB) WRITE (6,'(3A)') ' Memory: about ',
     $     TRIM(MIBD(BYTES)),
     $     ' MiB for the double-precision images'
      ALLOCATE (PIX(NCOL,NROW), STAT=IST)
      IF (IST .NE. 0) THEN
         CALL FITSCLOSE(IUNIT)
         CALL NOMEMD('the science image', 8D0*NPIX)
         RETURN
      END IF
      CALL FITSBITPIX(IUNIT, IBITPIX)
      CALL FITSREADPIXD(IUNIT, NCOL, NROW, PIX, IERR)
      IF (IERR .NE. 0) RETURN

      IM = 1
      IRBX = 1
      ICBX = 1
      BUFF(1) = .TRUE.
      ICOORD(NNROW,1) = NROW
      ICOORD(NNCOL,1) = NCOL
      ICOORD(IISR,1) = ISR
      ICOORD(IISC,1) = ISC
      ICOORD(IICMPR,1) = 1
      ICOORD(IICMPC,1) = 1
      WRITE (6,1000) FITSFILE(1:LEN_TRIM(FITSFILE)), NCOL, NROW,
     $     ISC, ISR
 1000 FORMAT (1X,A,': ',I6,' cols x',I6,' rows, origin (col,row) = (',
     $     I6,',',I6,')')
      WRITE (6,'(4A)') ' Precision: double (IEEE-754 binary64); ',
     $     'requested ', PRECREQ(1:LEN_TRIM(PRECREQ)),
     $     PRECWHY(1:LEN_TRIM(PRECWHY))
      WRITE (6,1002) IBITPIX
 1002 FORMAT (' Image: BITPIX ',I0,' read in double precision ',
     $     '(BSCALE/BZERO applied in double)')

C     ---- Check every other image before the science image changes

      IF (SKYIMG .NE. ' ') THEN
         CALL CHKSKYIMG(SKYIMG, NCOL, NROW, ISC, ISR, IERR)
         IF (IERR .NE. 0) RETURN
      END IF
      IF (MASKFILE .NE. ' ') THEN
         CALL CHKMASK(MASKFILE, NCOL, NROW, ISC, ISR, IERR)
         IF (IERR .NE. 0) RETURN
      END IF

C     ---- Sky, then mask: the order matters

      SKYDESC = 'none'
      NOVER = 0
      IF (SKYSTR .NE. ' ') THEN
         CALL SUBSKYD(PIX, NCOL, NROW, SKYVAL, NOVER)
         WRITE (6,1001) SKYVAL
 1001    FORMAT (' Sky: subtracted scalar ',1PE24.17E3)
         WRITE (SKYDESC,'(A,1PE24.17E3)') 'scalar ', SKYVAL
      ELSE IF (SKYIMG .NE. ' ') THEN
         CALL SUBSKYIMGD(SKYIMG, PIX, NCOL, NROW, ISC, ISR, NOVER,
     $        IERR)
         IF (IERR .NE. 0) RETURN
         WRITE (6,'(2A)') ' Sky: subtracted image ',
     $        SKYIMG(1:LEN_TRIM(SKYIMG))
         SKYDESC = 'image ' // SKYIMG
      END IF
      IF (NOVER .GT. 0) THEN
         WRITE (0,'(A,I0,A)') 'elliprof: error (double precision, '
     $        //'sky): science - sky is beyond the double range at ',
     $        NOVER, ' pixel(s)'
         RETURN
      END IF

      MSKDESC = 'none'
      IF (MASKFILE .NE. ' ' .OR. RESFILE .NE. ' ') THEN
         ALLOCATE (GOOD(NCOL,NROW), STAT=IST)
         IF (IST .NE. 0) THEN
            CALL NOMEMD('the logical mask', 4D0*NPIX)
            RETURN
         END IF
         GOOD = .TRUE.
      END IF
      IF (MASKFILE .NE. ' ') THEN
         CALL APPLYMASKD(MASKFILE, PIX, NCOL, NROW, ISC, ISR, ZGOOD,
     $        GOOD, MBITPIX, NBAD, NNONF, IERR)
         IF (IERR .NE. 0) RETURN
         WRITE (6,1003) MASKFILE(1:LEN_TRIM(MASKFILE)), MBITPIX,
     $        NBAD, 100D0*NBAD/(DBLE(NCOL)*NROW)
 1003    FORMAT (' Mask: ',A,' (BITPIX ',I0,'): ',I0,
     $        ' pixels masked (',F6.3,'%)')
         IF (NNONF .GT. 0) WRITE (6,'(A,I0,A)') ' Mask: ', NNONF,
     $        ' of them NaN, Inf or undefined'
         IF (ZGOOD) WRITE (6,'(A)') ' Mask: convention zero-good '
     $        //'(0 = good, nonzero = bad)'
         MSKDESC = MASKFILE
      END IF

C     ---- The normalization exponent (applied after the prepared
C     product is written, which stays in physical units)

      CALL NORMEXPD(PIX, NPIX, LINEAR, KPREF, KMIN, KMAX, KNORM,
     $     NINEX, NUSED)
      WRITE (6,1004) KNORM, KPREF, KMIN, KMAX
 1004 FORMAT (' Normalization: fit on image x 2**(-k), k = ',I0,
     $     ' (preferred ',I0,', safe ',I0,' to ',I0,')')
      IF (KNORM .NE. KPREF) WRITE (6,'(A)') ' Normalization: the '
     $     //'preferred k was clamped into the safe range'
      IF (NUSED .EQ. 0) WRITE (6,'(A)') ' Normalization: no finite '
     $     //'nonzero pixel; k = 0'
      IF (NINEX .GT. 0) WRITE (6,'(A,I0,A)') ' Normalization: ',
     $     NINEX, ' value(s) below the normal double range '
     $     //'internally, rounded'
      HIST(1) = 'elliprof precision: double (IEEE-754 binary64)'
      YESNO = 'no'
      IF (KNORM .NE. KPREF) YESNO = 'yes'
      WRITE (HIST(2),'(A,I0,A,I0,2A)') 'elliprof normalization: '
     $     //'k=', KNORM, ' preferred=', KPREF, ' clamped=', YESNO
      HIST(3) = 'elliprof normalization: fit on image x 2**(-k); '
     $     //'products physical'
      NHIST = 3

C     ---- The prepared image, physical units: good(mask) x (science -
C     sky), BITPIX -64

      IF (PREPFILE .NE. ' ') THEN
         CALL FITSWRITEPRODD(PREPFILE, FITSFILE, NCOL, NROW, PIX,
     $        'PREPARED = mask x (science - sky)', NHIST, HIST, IERR)
         IF (IERR .NE. 0) RETURN
      END IF
      IF (PREPONLY) THEN
         ISTAT = 0
         RETURN
      END IF

      WRITE (0,'(A)') 'elliprof: error (double precision, fit): '
     $     //'double-precision fitting is not enabled in this build'
      RETURN
      END
