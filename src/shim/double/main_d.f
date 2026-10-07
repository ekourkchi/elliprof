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
     $     PREPONLY, DOMODEL, PRECREQ, PRECWHY, NONFIN, NFREQ, ISTAT)
      CHARACTER*(*) FITSFILE, PRFFILE, MODFILE, CSVFILE, REGFILE
      CHARACTER*(*) MASKFILE, SKYIMG, SKYSTR, PREPFILE, RESFILE
      CHARACTER*(*) PRECREQ, PRECWHY, NONFIN, NFREQ
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
      INTEGER NOVER, IST, KPREF, KMIN, KMAX, I, J, K, NHIST, ICOS3X, L
      INTEGER NNAN, NPINF, NMINF
      INTEGER*8 NPIX, NUSED, NINEX
      LOGICAL LINEAR, SHVERB
      CHARACTER*1024 SKYDESC, MSKDESC
      CHARACTER*72 HIST(5)
      CHARACTER*3 YESNO
      CHARACTER*16 MIBD
      CHARACTER*512 PRECLN, NORMLN, UNDLN, SUBLN
      INTEGER NUNDT, NSUBT, NHM
      DOUBLE PRECISION V
      LOGICAL FINITED
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
C     memory: the per-pixel arrays -- the image, its prepared copy for
C     --residual, the logical mask, and the largest transient buffer
C     (a double sky image, or the mask read in double with its flags);
C     32 bytes per pixel with a mask and --residual.  A baseline, not
C     the peak use: fit arrays, CFITSIO buffers, the header and the run
C     time come on top.
      BYTES = 8D0*NPIX
      IF (RESFILE .NE. ' ') BYTES = BYTES + 8D0*NPIX
      IF (MASKFILE .NE. ' ' .OR. RESFILE .NE. ' ' .OR.
     $     NONFIN .NE. 'keep') BYTES = BYTES + 4D0*NPIX
      IF (MASKFILE .NE. ' ') THEN
         BYTES = BYTES + 12D0*NPIX
      ELSE IF (SKYIMG .NE. ' ') THEN
         BYTES = BYTES + 8D0*NPIX
      END IF
      IF (SHVERB) WRITE (6,'(3A)') ' Memory: about ',
     $     TRIM(MIBD(BYTES)),
     $     ' MiB for the per-pixel arrays (baseline; peak use is '
     $     //'higher)'
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
      IF (MASKFILE .NE. ' ' .OR. RESFILE .NE. ' ' .OR.
     $     NONFIN .NE. 'keep') THEN
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
      IF (NONFIN .EQ. 'mask') THEN
         CALL NONFIND(PIX, NCOL, NROW, GOOD, NNAN, NPINF, NMINF)
      ELSE
         CALL NONFCNTD(PIX, NCOL, NROW, NNAN, NPINF, NMINF)
      END IF
      CALL NONFINRPT(NNAN, NPINF, NMINF, NONFIN, NFREQ, 'double')
      IF (NNAN+NPINF+NMINF .GT. 0 .AND. NONFIN .EQ. 'error') RETURN

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
C     LINEAR fits intensities, squares and sums them (variances, the
C     least-squares sums over up to 360 samples): every internal value
C     must stay below 2**500.  KPREF is the exponent of the largest
C     value; only clamping (a range of values beyond about 2**1073)
C     can leave KNORM below it.  No safe k for LINEAR: an error.
      IF (LINEAR .AND. KPREF - KNORM .GT. 500) THEN
         WRITE (0,'(A,I0,A)') 'elliprof: error (double precision, '
     $        //'normalization): LINEAR needs the nonzero |values| '
     $        //'within a factor 2**', 1573, ' of each other; this '
     $        //'image spans more (use the default log fit, or mask '
     $        //'the extreme pixels)'
         RETURN
      END IF
      HIST(1) = 'elliprof precision: double (IEEE-754 binary64)'
      YESNO = 'no'
      IF (KNORM .NE. KPREF) YESNO = 'yes'
      WRITE (HIST(2),'(A,I0,A,I0,2A)') 'elliprof normalization: '
     $     //'k=', KNORM, ' preferred=', KPREF, ' clamped=', YESNO
      HIST(3) = 'elliprof normalization: fit on image x 2**(-k); '
     $     //'products physical'
      NHIST = 3
      UNDLN = ' '
      SUBLN = ' '

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
      NUNDER = 0
      NSUBN = 0
      NOVERM = 0
      MODPHY = .FALSE.
      CALL ELLIPROFD(PIX, NROW, NCOL)
      IF (DOMODEL .AND. SHVERB) WRITE (0,*)
C     Range failures of the double fit, never a silent success: an
C     isophote intensity I0 that is +-Inf (an iterate beyond the double
C     range), or a slope d ln I / d ln r that is +-Inf although its own
C     I0 is finite and nonzero (the original's linear difference
C     (I(k-1) - I(k+1)) / I(k) beyond the double range).  Other
C     non-finite values are left as they are: the original algorithm
C     gives NaN or Inf in degenerate fits (a 6th-order amplitude on a
C     tiny isophote, ...).  In a log fit an I0 of exactly 0 is also a
C     range failure: I0 is only ever multiplied by exp(c) there, so 0
C     means exp(c) underflowed although f0*exp(c) may not.
      CALL PRFINFD(K, J, LINEAR)
      IF (K .GT. 0 .AND. J .EQ. 4) WRITE (0,'(A,I0,A)') 'elliprof: '
     $     //'error (double precision, fit): the intensity I0 of '
     $     //'isophote ', K, ' overflowed the double range during the '
     $     //'fit'
      IF (K .GT. 0 .AND. J .EQ. 0) WRITE (0,'(A,I0,A)') 'elliprof: '
     $     //'error (double precision, fit): the intensity I0 of '
     $     //'isophote ', K, ' underflowed to zero during the fit (an '
     $     //'intermediate exp below the double range)'
      IF (K .GT. 0 .AND. J .EQ. 11) WRITE (0,'(A,I0,A)') 'elliprof: '
     $     //'error (double precision, fit): the slope dlnI/dlnr of '
     $     //'isophote ', K, ' is beyond the double range '
     $     //'(neighbouring intensities differ by more than DBL_MAX)'
      IF (XERR) THEN
         WRITE (0,'(A)') 'elliprof: error (double precision, fit): '
     $        //'ELLIPROF reported an error'
         RETURN
      END IF
      IF (K .GT. 0) RETURN
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

C     ---- The model in physical units.  SYNTHESIZED returns it so
C     (MODPHY, R6: normalization never turns a representable physical
C     model into 0 or Inf) and counts, in physical units, the pixels
C     whose model underflowed to zero, is subnormal, or is beyond the
C     double range.  Otherwise PIX is in internal units and is scaled
C     here, exactly, as before.  A finite value beyond the double range
C     is an error, never a silent Inf.  (A NaN that the original model
C     algorithm gives stays NaN, as in single.)  Underflow to zero and
C     subnormal values are reported, for information.

      NUNDT = 0
      NSUBT = 0
      NHM = NHIST
      IF (DOMODEL .AND. MODPHY) THEN
         NOVER = NOVERM
         NUNDT = NUNDER
         NSUBT = NSUBN
      ELSE IF (DOMODEL) THEN
         NOVER = 0
         NUNDT = NUNDER
         DO 60 J = 1, NROW
            DO 61 I = 1, NCOL
               V = PIX(I,J)
               PIX(I,J) = SCALE(V, KNORM)
               IF (FINITED(V) .AND. .NOT. FINITED(PIX(I,J)))
     $              NOVER = NOVER + 1
               IF (V .NE. 0 .AND. PIX(I,J) .EQ. 0) NUNDT = NUNDT + 1
               IF (PIX(I,J) .NE. 0 .AND. ABS(PIX(I,J)) .LT. TINY(V))
     $              NSUBT = NSUBT + 1
 61         CONTINUE
 60      CONTINUE
      END IF
      IF (DOMODEL) THEN
         IF (NOVER .GT. 0) THEN
            WRITE (0,'(A,I0,A)') 'elliprof: error (double precision, '
     $           //'model): the model is beyond the double range at ',
     $           NOVER, ' pixel(s) in physical units'
            RETURN
         END IF
         IF (NUNDT .GT. 0) WRITE (6,'(A,I0,A)') ' Model: ', NUNDT,
     $        ' pixels underflowed to zero at double precision.'
         IF (NSUBT .GT. 0) WRITE (6,'(A,I0,A)') ' Model: ', NSUBT,
     $        ' pixels are subnormal (nonzero, below the normal double'
     $        //' range: reduced precision).'
         WRITE (HIST(NHIST+1),'(A,I0,A)') 'elliprof model underflow '
     $        //'to zero: ', NUNDT, ' pixel(s)'
         WRITE (HIST(NHIST+2),'(A,I0,A)') 'elliprof model subnormal '
     $        //'(nonzero): ', NSUBT, ' pixel(s)'
         NHM = NHIST + 2
         WRITE (UNDLN,'(I0,A)') NUNDT, ' pixel(s)'
         WRITE (SUBLN,'(I0,A)') NSUBT, ' pixel(s)'
      END IF

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

C     ---- CSV table and DS9 regions

      WRITE (PRECLN,'(4A)') 'double (IEEE-754 binary64); requested ',
     $     PRECREQ(1:LEN_TRIM(PRECREQ)), PRECWHY(1:LEN_TRIM(PRECWHY))
      WRITE (NORMLN,'(A,I0,A,I0,3A)') 'k=', KNORM, ' preferred=',
     $     KPREF, ' clamped=', YESNO(1:LEN_TRIM(YESNO)),
     $     ' (fit on image x 2**(-k); values in physical units)'
      IF (CSVFILE .NE. ' ') THEN
         L = LEN_TRIM(ORIGCOMMAND)
         CALL WRITECSVD(CSVFILE, FITSFILE, MSKDESC, SKYDESC,
     $        ORIGCOMMAND(10:MAX(10,L)), ISC, ISR, PRECLN, NORMLN,
     $        UNDLN, SUBLN, IERR)
         IF (IERR .NE. 0) RETURN
      END IF
      IF (REGFILE .NE. ' ') THEN
         CALL WRITEREGD(REGFILE, ISC, ISR, IERR)
         IF (IERR .NE. 0) RETURN
      END IF

      IF (MODFILE .NE. ' ') THEN
         CALL FITSWRITEPRODD(MODFILE, FITSFILE, NCOL, NROW, PIX,
     $        'MODEL (galaxy model from the fitted isophotes)',
     $        NHM, HIST, IERR)
         IF (IERR .NE. 0) RETURN
      END IF

C     ---- The residual from that model, in physical units:
C     good(mask) x (science - sky - model)

      IF (RESFILE .NE. ' ') THEN
         NOVER = 0
         DO 70 J = 1, NROW
            DO 71 I = 1, NCOL
               IF (GOOD(I,J)) THEN
                  V = PREP(I,J)
                  PREP(I,J) = V - PIX(I,J)
                  IF (FINITED(V) .AND. FINITED(PIX(I,J)) .AND.
     $                 .NOT. FINITED(PREP(I,J))) NOVER = NOVER + 1
               ELSE
                  PREP(I,J) = 0
               END IF
 71         CONTINUE
 70      CONTINUE
         IF (NOVER .GT. 0) THEN
            WRITE (0,'(A,I0,A)') 'elliprof: error (double precision, '
     $           //'residual): prepared - model is beyond the double '
     $           //'range at ', NOVER, ' pixel(s)'
            RETURN
         END IF
         CALL FITSWRITEPRODD(RESFILE, FITSFILE, NCOL, NROW, PREP,
     $        'RESIDUAL = mask x (science - sky - model)', NHM,
     $        HIST, IERR)
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
C     SYNTHESIZED (pi in double precision).
      SUBROUTINE PAWRAPD(N, PRM, K)
      INTEGER N, K, I
      DOUBLE PRECISION PRM(12,*), TH, THPREV, D, PI, Q
      PARAMETER (PI=4D0*ATAN(1D0))
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

C     The first isophote K with a range failure (see the caller): J = 4
C     if its I0 is +-Inf, J = 0 if its I0 is exactly 0 in a log fit
C     (LINEAR false), J = 11 if its slope is +-Inf while its I0 is
C     finite and nonzero; K = 0 if none.
      SUBROUTINE PRFINFD(K, J, LINEAR)
      INTEGER K, J, I
      LOGICAL LINEAR
      DOUBLE PRECISION A
      INCLUDE 'profile_d.inc'
      K = 0
      J = 0
      DO 10 I = 1, N_PRF
         A = ABS(PARAM_PRF(4,I))
         IF (A .GT. HUGE(A)) THEN
            K = I
            J = 4
            RETURN
         END IF
         IF (A .EQ. 0 .AND. .NOT. LINEAR) THEN
            K = I
            J = 0
            RETURN
         END IF
         IF (ABS(PARAM_PRF(11,I)) .GT. HUGE(A) .AND. A .GT. 0) THEN
            K = I
            J = 11
            RETURN
         END IF
 10   CONTINUE
      RETURN
      END
