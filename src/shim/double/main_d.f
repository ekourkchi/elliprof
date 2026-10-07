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
      INTEGER NOVER, IST, KPREF, KMIN, KMAX, I, J, K, NHIST, ICOS3X
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

C     ELLIPROFD replaces the image with its model: keep the prepared
C     image (physical units) for the residual
      IF (RESFILE .NE. ' ') THEN
         ALLOCATE (PREP(NCOL,NROW), STAT=IST)
         IF (IST .NE. 0) THEN
            CALL NOMEMD('the prepared image for --residual', 8D0*NPIX)
            RETURN
         END IF
         PREP = PIX
      END IF

C     ---- The fit, on the normalized image

      CALL SCALEIMD(PIX, NPIX, -KNORM)
      CALL ELLIPROFD(PIX, NROW, NCOL)
      IF (DOMODEL .AND. SHVERB) WRITE (0,*)
      IF (XERR) THEN
         WRITE (0,'(A)') 'elliprof: error (double precision, fit): '
     $        //'ELLIPROF reported an error'
         RETURN
      END IF
      IF (N_PRF .LE. 0) THEN
         WRITE (0,'(A)') 'elliprof: error (double precision, fit): '
     $        //'no profile was computed'
         RETURN
      END IF

C     ---- Back to physical units: I0 of every isophote (the only
C     intensity of the profile; the harmonic amplitudes, slope and
C     flags are dimensionless), exactly

      DO 50 I = 1, N_PRF
         PARAM_PRF(4,I) = SCALE(PARAM_PRF(4,I), KNORM)
 50   CONTINUE
      CALL PRFMARKD(KNORM, KPREF)

C     A 6th-order term in the model and a PA wrap: as in main.f
      IF (DOMODEL .AND. N_PRF .GT. 1) THEN
         ICOS3X = NINT(PARAM_PRF(12,15))
         IF (ICOS3X .EQ. -1 .OR. ICOS3X .EQ. -2) THEN
            CALL PAWRAPD(N_PRF, PARAM_PRF, K)
            IF (K .GT. 0) WRITE (0,'(A,I0,A,F0.1,6A)')
     $           'elliprof: warning: the fitted PA wraps across 0/180'//
     $           ' deg at isophote ', K, ' (Rmaj = ', PARAM_PRF(1,K),
     $           '). The 6th-order measurements are valid, but the ',
     $           'original model synthesis gives the 6th-order term ',
     $           'the wrong sign beyond the wrap: the model and ',
     $           'residual may be wrong there. COS3X=-3 ',
     $           '(--sixth-order --model-harmonics none) measures ',
     $           'without modelling.'
         END IF
      END IF

C     ---- The profile table (as main.f), I0 in a format for the whole
C     double range

      IF (SHVERB .OR. (PRFFILE .EQ. ' ' .AND. CSVFILE .EQ. ' ')) THEN
         WRITE (6,103)
 103     FORMAT (' SURFACE PHOTOMETRY PROFILE COMPUTATION: ')
         IF (NINT(PARAM_PRF(12,15)) .GE. 0) THEN
            WRITE (6,105)
         ELSE
            WRITE (6,107)
         END IF
 105     FORMAT ('  Rmaj     x0      y0           I0        alpha ',
     $        'ellip  I(3x)  A(3x)  I(4x)  A(4x) slope')
 107     FORMAT ('  Rmaj     x0      y0           I0        alpha ',
     $        'ellip  I(6x)  A(6x)  I(4x)  A(4x) slope')
         DO 55 I = 1, N_PRF
            WRITE (6,106) (PARAM_PRF(J,I),J=1,11)
 106        FORMAT (F6.1,2F8.2,1X,1PE16.8E3,0P,F7.2,F6.3,
     $           2(F7.4,F7.2),F6.2)
 55      CONTINUE
      END IF

C     ---- The profile (-o): the layout of SAVE ELLIPROF=file ASCII,
C     every value with 18 significant digits and a 3-digit exponent

      IF (PRFFILE .NE. ' ') THEN
         CALL WRITEDATD(PRFFILE, IERR)
         IF (IERR .NE. 0) RETURN
      END IF

      ISTAT = 0
      RETURN
      END

C     The double profile is marked in its header text: HISTORY cards,
C     inserted before END, give the precision and the normalization.
C     (Row 12 of PARAM_PRF holds the run flags and, in the original
C     MONSTA, other per-contour values: no slot is free for a marker.)
      SUBROUTINE PRFMARKD(KNORM, KPREF)
      INTEGER KNORM, KPREF
      INCLUDE 'profile_d.inc'
      INTEGER IEND, NCARD, MAXC
      CHARACTER*80 C1, C2, C3
      MAXC = LEN(PRF_HEAD) / 80
      IEND = 0
      DO 10 NCARD = 1, MAXC
         IF (PRF_HEAD((NCARD-1)*80+1:(NCARD-1)*80+8) .EQ. 'END') THEN
            IEND = NCARD
            GOTO 11
         END IF
 10   CONTINUE
 11   IF (IEND .EQ. 0) IEND = MAXC
C     room for three cards and END: drop the last header cards if needed
      IF (IEND + 3 .GT. MAXC) THEN
         WRITE (0,'(A,I0,A)') 'elliprof: note: the header is full; ',
     $        IEND + 3 - MAXC, ' card(s) at its end not kept in the '
     $        //'profile'
         IEND = MAXC - 3
      END IF
      C1 = 'HISTORY elliprof profile precision: double (IEEE-754 '
     $     //'binary64)'
      WRITE (C2,'(A,I0,A,I0)') 'HISTORY elliprof profile '
     $     //'normalization: k=', KNORM, ' preferred=', KPREF
      C3 = 'HISTORY elliprof profile: I0 in physical units'
      PRF_HEAD((IEND-1)*80+1:(IEND-1)*80+80) = C1
      PRF_HEAD(IEND*80+1:IEND*80+80) = C2
      PRF_HEAD((IEND+1)*80+1:(IEND+1)*80+80) = C3
      PRF_HEAD((IEND+2)*80+1:(IEND+2)*80+80) = 'END'
      RETURN
      END

C     -o FILE: N_PRF, PRF_SC, PARAM_PRF(12,250), header text, in that
C     order (as the single backend's list-directed WRITE), each number
C     as ES25.17E3: 18 significant digits (17 suffice to give back the
C     same double) and an explicit 3-digit exponent, so every finite
C     double from 4.9E-324 to 1.8E+308 is written readably.
      SUBROUTINE WRITEDATD(FNAME, IERR)
      CHARACTER*(*) FNAME
      INTEGER IERR
      INCLUDE 'profile_d.inc'
      OPEN (4, FILE=FNAME, FORM='FORMATTED', STATUS='UNKNOWN',
     $     IOSTAT=IERR)
      IF (IERR .NE. 0) THEN
         WRITE (0,'(3A)') 'elliprof: error (double precision, output):'
     $        //' cannot open ', FNAME(1:LEN_TRIM(FNAME))
         RETURN
      END IF
      WRITE (4,'(1X,I0)') N_PRF
      WRITE (4,'(1X,ES25.17E3)') PRF_SC
      WRITE (4,'(4(1X,ES25.17E3))') PARAM_PRF
      WRITE (4,'(1X,A)') PRF_HEAD(1:LEN_TRIM(PRF_HEAD))
      CLOSE (4)
      RETURN
      END

C     PAWRAP (main.f) for the double profile, with the arithmetic of
C     SYNTHESIZED.
      SUBROUTINE PAWRAPD(N, PRM, K)
      INTEGER N, K, I
      DOUBLE PRECISION PRM(12,*), TH, THPREV, D, PI, Q
      PARAMETER (PI=3.14159265D0)
      Q = 180/PI
      K = 0
      THPREV = (PRM(5,1) + 90) / Q
      DO 10 I = 2, N
         TH = (PRM(5,I) + 90) / Q
         D = PI * ANINT((TH - THPREV) / PI)
         IF (D .NE. 0 .AND. K .EQ. 0) K = I
         THPREV = TH - D
 10   CONTINUE
      RETURN
      END
