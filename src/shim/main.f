C     elliprof_native: the compiled backend of the elliprof package.
C
C     Runs MONSTA/VISTA's ELLIPROF, compiled unchanged from
C     src/original, on one FITS image.  This program replaces only the
C     parts of VISTA that normally surround ELLIPROF: reading the image
C     (RD), preparing it (SC/SI/MI, see prep.f), splitting the command
C     line into WORD() the way vista.f does, setting GO/XERR/NOGO and
C     the image origin ISR/ISC, and writing the result the way
C     PRINT EPROF and SAVE ELLIPROF=file ASCII do.
C
C     The centre must be given as X0= Y0= in ELLIPROF's own
C     coordinates.  Automatic, physical and RA/DEC centres are
C     handled by the Python `elliprof` command, which converts them to
C     X0/Y0 before calling this program.

      PROGRAM ELLIPROFMAIN
      USE, INTRINSIC :: ISO_FORTRAN_ENV, ONLY: COMPILER_VERSION
      INCLUDE 'vistalink.inc'
      INCLUDE 'imagelink.inc'
      INCLUDE 'profile.inc'
      INCLUDE 'version.inc'

      REAL, ALLOCATABLE :: PIX(:,:)
      CHARACTER*1024 ARG, FITSFILE, PRFFILE, MODFILE, CSVFILE, REGFILE
      CHARACTER*1024 MASKFILE, SKYIMG, SKYSTR, CTRSRC, SKYDESC, MSKDESC
      CHARACTER*1024 PREPFILE
      CHARACTER*289 OSTRNG, LCSTRNG
      LOGICAL ERR, DOMODEL, DOGC, HASX0, HASY0, HASR0, HASR1, HASNR
      LOGICAL PREPONLY
      INTEGER UPPER, NARGS, IARG, IWORD, JCHAR, IB, ICON, NSKYOPT
      INTEGER NTYPE, NUM, NCHAR, NCOL, NROW, IUNIT, IERR, L, I, J
      INTEGER ICOS3X, MBITPIX, NZERO, NOTHER
      REAL FNUM, SKYVAL, CFV

C     ---- Command line: image file, options, ELLIPROF words

      NARGS = COMMAND_ARGUMENT_COUNT()
      FITSFILE = ' '
      PRFFILE = ' '
      MODFILE = ' '
      CSVFILE = ' '
      REGFILE = ' '
      MASKFILE = ' '
      SKYSTR = ' '
      SKYIMG = ' '
      CTRSRC = 'explicit X0/Y0'
      PREPFILE = ' '
      PREPONLY = .FALSE.
      NSKYOPT = 0
      COMMAND = 'ELLIPROF'
      IARG = 0
 10   IARG = IARG + 1
      IF (IARG .GT. NARGS) GOTO 20
      CALL GET_COMMAND_ARGUMENT(IARG, ARG)
      IF (ARG .EQ. '-h' .OR. ARG .EQ. '--help') THEN
         CALL USAGE(6)
         STOP
      ELSE IF (ARG .EQ. '--version') THEN
C     CFITSIO reports its version as major + minor/100
         CALL FITSLIBVER(CFV)
         WRITE (6,'(3A,I0,A,I0,3A)') 'elliprof_native ', VERSTR,
     $        ' (CFITSIO ', INT(CFV), '.', NINT((CFV-INT(CFV))*100),
     $        '; ', COMPILER_VERSION(), ')'
         STOP
      ELSE IF (ARG .EQ. '--prepare-only') THEN
         PREPONLY = .TRUE.
      ELSE IF (ARG .EQ. '-o' .OR. ARG .EQ. '-m' .OR.
     $        ARG .EQ. '--csv' .OR. ARG .EQ. '--reg' .OR.
     $        ARG .EQ. '--mask' .OR. ARG .EQ. '--sky' .OR.
     $        ARG .EQ. '--sc' .OR. ARG .EQ. '--sky-image' .OR.
     $        ARG .EQ. '--center-source' .OR.
     $        ARG .EQ. '--prepared') THEN
         IF (IARG .EQ. NARGS) THEN
            WRITE (0,*) 'elliprof: ', ARG(1:LEN_TRIM(ARG)),
     $           ' needs a value'
            CALL EXIT(1)
         END IF
         IARG = IARG + 1
         IF (ARG .EQ. '-o') THEN
            CALL GET_COMMAND_ARGUMENT(IARG, PRFFILE)
         ELSE IF (ARG .EQ. '-m') THEN
            CALL GET_COMMAND_ARGUMENT(IARG, MODFILE)
         ELSE IF (ARG .EQ. '--csv') THEN
            CALL GET_COMMAND_ARGUMENT(IARG, CSVFILE)
         ELSE IF (ARG .EQ. '--reg') THEN
            CALL GET_COMMAND_ARGUMENT(IARG, REGFILE)
         ELSE IF (ARG .EQ. '--mask') THEN
            CALL GET_COMMAND_ARGUMENT(IARG, MASKFILE)
         ELSE IF (ARG .EQ. '--sky-image') THEN
            CALL GET_COMMAND_ARGUMENT(IARG, SKYIMG)
            NSKYOPT = NSKYOPT + 1
         ELSE IF (ARG .EQ. '--center-source') THEN
            CALL GET_COMMAND_ARGUMENT(IARG, CTRSRC)
         ELSE IF (ARG .EQ. '--prepared') THEN
            CALL GET_COMMAND_ARGUMENT(IARG, PREPFILE)
         ELSE
            IF (ARG .EQ. '--sc') WRITE (0,'(A)')
     $           ' elliprof: --sc is deprecated, use --sky'
            CALL GET_COMMAND_ARGUMENT(IARG, SKYSTR)
            NSKYOPT = NSKYOPT + 1
         END IF
      ELSE IF (ARG(1:1) .EQ. '-') THEN
         WRITE (0,*) 'elliprof: unknown option ', ARG(1:LEN_TRIM(ARG))
         CALL EXIT(1)
      ELSE IF (FITSFILE .EQ. ' ') THEN
         FITSFILE = ARG
      ELSE
         L = LEN_TRIM(COMMAND)
         IF (L + 1 + LEN_TRIM(ARG) .GT. LEN(COMMAND)) THEN
            WRITE (0,*) 'elliprof: command line longer than',
     $           LEN(COMMAND), ' characters'
            CALL EXIT(1)
         END IF
         COMMAND = COMMAND(1:L) // ' ' // ARG
      END IF
      GOTO 10

 20   IF (FITSFILE .EQ. ' ') THEN
         CALL USAGE(0)
         CALL EXIT(1)
      END IF
      IF (NSKYOPT .GT. 1) THEN
         WRITE (0,'(A)') ' elliprof: give only one of --sky (or --sc)'
     $        //' and --sky-image'
         CALL EXIT(1)
      END IF

C     ---- Tokenise exactly as vista.f does: UPPER, then DISSECT each
C     word.  Integers and floats go to IBUF/CONST (in MONSTA the
C     first integer is the image buffer number), strings to WORD.

      ORIGCOMMAND = COMMAND
      L = UPPER(COMMAND)
      DO 25 I = 1, NCON
         IBUF(I) = 0
         CONST(I) = 0.0
         WORD(I) = ' '
         ORIGWORD(I) = ' '
         IDXWORD(I) = 0
         IDXINT(I) = 0
         IDXFLOAT(I) = 0
 25   CONTINUE
      IB = 0
      ICON = 0
      JCHAR = 0
      IWORD = 0
 30   IWORD = IWORD + 1
      CALL DISSECT(COMMAND, IWORD, .FALSE., NTYPE, NUM, FNUM,
     $     OSTRNG, NCHAR, ERR)
      IF (ERR) GOTO 40
      IF (IWORD .EQ. 1) THEN
         COM = OSTRNG
      ELSE IF (NTYPE .EQ. 1) THEN
         IB = IB + 1
         IF (IB .LE. NCON) THEN
            IBUF(IB) = NUM
            IDXINT(IB) = IWORD
         END IF
      ELSE IF (NTYPE .EQ. 2) THEN
         ICON = ICON + 1
         IF (ICON .LE. NCON) THEN
            CONST(ICON) = FNUM
            IDXFLOAT(ICON) = IWORD
         END IF
      ELSE
         CALL DISSECT(ORIGCOMMAND, IWORD, .FALSE., NTYPE, NUM, FNUM,
     $        LCSTRNG, NCHAR, ERR)
         JCHAR = JCHAR + 1
         IF (JCHAR .LE. NCON) THEN
            WORD(JCHAR) = OSTRNG
            ORIGWORD(JCHAR) = LCSTRNG
            IDXWORD(JCHAR) = IWORD
         ELSE
            WRITE (0,*) 'elliprof: more than', NCON,
     $           ' keywords; ignoring ', LCSTRNG(1:NCHAR)
         END IF
      END IF
      GOTO 30
 40   CONTINUE

      DOMODEL = .FALSE.
      DOGC = .FALSE.
      HASX0 = .FALSE.
      HASY0 = .FALSE.
      HASR0 = .FALSE.
      HASR1 = .FALSE.
      HASNR = .FALSE.
      DO 45 I = 1, NCON
         IF (WORD(I) .EQ. 'MODEL') DOMODEL = .TRUE.
         IF (WORD(I) .EQ. 'GC') DOGC = .TRUE.
         IF (WORD(I)(1:3) .EQ. 'X0=') HASX0 = .TRUE.
         IF (WORD(I)(1:3) .EQ. 'Y0=') HASY0 = .TRUE.
         IF (WORD(I)(1:3) .EQ. 'R0=') HASR0 = .TRUE.
         IF (WORD(I)(1:3) .EQ. 'R1=') HASR1 = .TRUE.
         IF (WORD(I)(1:3) .EQ. 'NR=') HASNR = .TRUE.
 45   CONTINUE

C     ---- Checks that ELLIPROF itself would only report after the
C     image had been read, or not clearly

      IF (PREPONLY) THEN
         IF (PREPFILE .EQ. ' ') THEN
            WRITE (0,'(A)') ' elliprof: --prepare-only needs --prepared'
            CALL EXIT(1)
         END IF
      ELSE IF (.NOT. HASX0 .AND. .NOT. HASY0) THEN
         WRITE (0,'(A)') ' X0 and Y0 are required by elliprof_native.'
         WRITE (0,'(A)') ' Use the Python `elliprof` command for'
     $        //' automatic image-center, physical-coordinate, or'
     $        //' RA/DEC handling.'
         CALL EXIT(1)
      ELSE IF (.NOT. HASX0 .OR. .NOT. HASY0) THEN
         WRITE (0,'(A)') ' elliprof: X0= and Y0= must be given'
     $        //' together'
         CALL EXIT(1)
      END IF
      DO 46 I = 1, NCON
         IF (WORD(I) .EQ. 'OLD' .OR. WORD(I) .EQ. 'EDIT') THEN
            L = LEN_TRIM(WORD(I))
            WRITE (0,'(3A)') ' elliprof: ', WORD(I)(1:L),
     $           ' needs a previous profile in memory, which this'
     $           //' program cannot load yet (not supported)'
            CALL EXIT(1)
         END IF
 46   CONTINUE
      IF (PREPONLY) THEN
         CONTINUE
      ELSE IF (DOGC .AND. .NOT. HASNR) THEN
         WRITE (0,'(A)') ' elliprof: GC needs NR='
         CALL EXIT(1)
      ELSE IF (.NOT. DOGC .AND.
     $        (.NOT. HASR0 .OR. .NOT. HASR1 .OR. .NOT. HASNR)) THEN
         WRITE (0,'(A)') ' elliprof: R0=, R1= and NR= are required'
         CALL EXIT(1)
      END IF
      IF (SKYSTR .NE. ' ') THEN
         CALL PARSENUM(SKYSTR, SKYVAL, IERR)
         IF (IERR .NE. 0) THEN
            WRITE (0,*) 'elliprof: --sky needs one number, got ',
     $           SKYSTR(1:LEN_TRIM(SKYSTR))
            CALL EXIT(1)
         END IF
      END IF
      CALL CHKOUT(PRFFILE, IERR)
      IF (IERR .EQ. 0) CALL CHKOUT(CSVFILE, IERR)
      IF (IERR .EQ. 0) CALL CHKOUT(REGFILE, IERR)
      IF (IERR .EQ. 0) CALL CHKOUT(MODFILE, IERR)
      IF (IERR .EQ. 0) CALL CHKOUT(PREPFILE, IERR)
      IF (IERR .NE. 0) CALL EXIT(1)

C     ---- VISTA control flags

      GO = .TRUE.
      CHECK = .TRUE.
      XERR = .FALSE.
      NOGO = .FALSE.
      XEOF = .FALSE.
      MONSTA = 1
      TTYLUN = 6
      REDIRLUN = 6

C     ---- Read the image into buffer 1 (what RD 1 file does)

      CALL FITSOPENIM(FITSFILE, IUNIT, NCOL, NROW, ISC, ISR,
     $     HEADBUF(1), IERR)
      IF (IERR .NE. 0) CALL EXIT(1)
      ALLOCATE (PIX(NCOL,NROW))
      CALL FITSREADPIX(IUNIT, NCOL, NROW, PIX, IERR)
      IF (IERR .NE. 0) CALL EXIT(1)

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
      IF (.NOT. PREPONLY) WRITE (6,'(2A)') ' Center source: ',
     $     CTRSRC(1:LEN_TRIM(CTRSRC))

C     ---- Sky, then mask (prep.f): the order matters

      SKYDESC = 'none'
      IF (SKYSTR .NE. ' ') THEN
         CALL SUBSKY(PIX, NCOL, NROW, SKYVAL)
         WRITE (6,1001) SKYVAL
 1001    FORMAT (' Sky: subtracted scalar',1PG16.8)
         WRITE (SKYDESC,'(A,G0)') 'scalar ', SKYVAL
      ELSE IF (SKYIMG .NE. ' ') THEN
         CALL SUBSKYIMG(SKYIMG, PIX, NCOL, NROW, ISC, ISR, IERR)
         IF (IERR .NE. 0) CALL EXIT(1)
         WRITE (6,'(2A)') ' Sky: subtracted image ',
     $        SKYIMG(1:LEN_TRIM(SKYIMG))
         SKYDESC = 'image ' // SKYIMG
      END IF

      MSKDESC = 'none'
      IF (MASKFILE .NE. ' ') THEN
         CALL APPLYMASK(MASKFILE, PIX, NCOL, NROW, ISC, ISR,
     $        MBITPIX, NZERO, NOTHER, IERR)
         IF (IERR .NE. 0) CALL EXIT(1)
         WRITE (6,1003) MASKFILE(1:LEN_TRIM(MASKFILE)), MBITPIX,
     $        NZERO, 100.0*NZERO/(FLOAT(NCOL)*NROW)
 1003    FORMAT (' Mask: ',A,' (BITPIX ',I0,'): ',I0,
     $        ' pixels masked (',F6.3,'%)')
         IF (NOTHER .GT. 0) WRITE (0,*) 'elliprof: ', NOTHER,
     $        ' mask pixels are neither 0 nor 1;',
     $        ' they multiply the image'
         MSKDESC = MASKFILE
      END IF

C     ---- Diagnostic: the image exactly as ELLIPROF receives it

      IF (PREPFILE .NE. ' ') THEN
         CALL FITSWRITEIM(PREPFILE, NCOL, NROW, PIX, ISC, ISR,
     $        'elliprof: image after sky and mask, input to ELLIPROF',
     $        IERR)
         IF (IERR .NE. 0) CALL EXIT(1)
      END IF
      IF (PREPONLY) STOP

C     ---- Run the unchanged ELLIPROF

      CALL ELLIPROF(PIX, NROW, NCOL)
      IF (DOMODEL) WRITE (0,*)

      IF (XERR) THEN
         WRITE (0,*) 'elliprof: ELLIPROF reported an error'
         CALL EXIT(1)
      END IF

C     ---- Print the profile the way PRINT EPROF does (printout.f)

      IF (N_PRF .GT. 0) THEN
         WRITE (6,103)
 103     FORMAT (' SURFACE PHOTOMETRY PROFILE COMPUTATION: ')
         ICOS3X = NINT(PARAM_PRF(12,15))
         IF (ICOS3X .GE. 0) THEN
            WRITE (6,105)
         ELSE
            WRITE (6,107)
         END IF
 105     FORMAT ('  Rmaj     x0      y0      I0    alpha ellip',
     $        '  I(3x)  A(3x)  I(4x)  A(4x) slope')
 107     FORMAT ('  Rmaj     x0      y0      I0    alpha ellip',
     $        '  I(6x)  A(6x)  I(4x)  A(4x) slope')
         DO 50 I = 1, N_PRF
            WRITE (6,106) (PARAM_PRF(J,I),J=1,11)
 106        FORMAT (F6.1,2F8.2,F9.1,F7.2,F6.3,2(F7.4,F7.2),F6.2)
 50      CONTINUE
      ELSE IF (.NOT. DOGC) THEN
         WRITE (0,*) 'elliprof: no profile was computed'
         CALL EXIT(1)
      END IF

C     ---- Save the profile the way SAVE ELLIPROF=file ASCII does

      IF (PRFFILE .NE. ' ') THEN
         IF (N_PRF .GT. 0) THEN
            OPEN (4, FILE=PRFFILE, FORM='FORMATTED', STATUS='UNKNOWN',
     $           IOSTAT=IERR)
            IF (IERR .NE. 0) THEN
               WRITE (0,*) 'elliprof: cannot open ',
     $              PRFFILE(1:LEN_TRIM(PRFFILE))
               CALL EXIT(1)
            END IF
            WRITE (4,*) N_PRF, PRF_SC, PARAM_PRF, PRF_HEAD
            CLOSE (4)
         ELSE
            WRITE (0,*) 'elliprof: -o ignored, GC mode has no profile'
         END IF
      END IF

C     ---- Optional CSV table and DS9 regions from the final /PRF/

      IF (CSVFILE .NE. ' ' .OR. REGFILE .NE. ' ') THEN
         IF (N_PRF .GT. 0) THEN
            IF (CSVFILE .NE. ' ') THEN
               CALL WRITECSV(CSVFILE, FITSFILE, MSKDESC, SKYDESC,
     $              CTRSRC, ISC, ISR, IERR)
               IF (IERR .NE. 0) CALL EXIT(1)
            END IF
            IF (REGFILE .NE. ' ') THEN
               CALL WRITEREG(REGFILE, ISC, ISR, IERR)
               IF (IERR .NE. 0) CALL EXIT(1)
            END IF
         ELSE
            WRITE (0,*) 'elliprof: --csv/--reg ignored,',
     $           ' GC mode has no profile'
         END IF
      END IF

C     ---- Write the model image, which ELLIPROF left in PIX

      IF (MODFILE .NE. ' ') THEN
         IF (DOMODEL) THEN
            CALL FITSWRITEIM(MODFILE, NCOL, NROW, PIX, ISC, ISR,
     $           'Model image from standalone ELLIPROF', IERR)
            IF (IERR .NE. 0) CALL EXIT(1)
         ELSE
            WRITE (0,*) 'elliprof: -m ignored, MODEL was not given'
         END IF
      ELSE IF (DOMODEL) THEN
         WRITE (0,*) 'elliprof: MODEL given without -m file;',
     $        ' model image not saved'
      END IF

      END

C     Fail early if an output file cannot be written.  A file created
C     only for the test is removed again; an existing one is kept.
      SUBROUTINE CHKOUT(FNAME, IERR)
      CHARACTER*(*) FNAME
      INTEGER IERR
      LOGICAL EXISTS
      IERR = 0
      IF (FNAME .EQ. ' ') RETURN
      INQUIRE (FILE=FNAME, EXIST=EXISTS)
      OPEN (9, FILE=FNAME, FORM='FORMATTED', STATUS='UNKNOWN',
     $     IOSTAT=IERR)
      IF (IERR .NE. 0) THEN
         WRITE (0,*) 'elliprof: cannot write output file ',
     $        FNAME(1:LEN_TRIM(FNAME))
         RETURN
      END IF
      IF (EXISTS) THEN
         CLOSE (9)
      ELSE
         CLOSE (9, STATUS='DELETE')
      END IF
      RETURN
      END

      SUBROUTINE USAGE(LUN)
      INTEGER LUN
      WRITE (LUN,'(A)')
     $ 'usage: elliprof_native image.fits X0=x Y0=y R0=r R1=r NR=n',
     $ '         [KEY=value ...] [--sky value | --sky-image file]',
     $ '         [--mask file] [-o out.prf] [--csv out.csv]',
     $ '         [--reg out.reg] [-m model.fits]',
     $ ' ',
     $ '  The compiled backend of the elliprof package.  Most users',
     $ '  should run the Python `elliprof` command instead, which also',
     $ '  finds the centre automatically or from physical or RA/DEC',
     $ '  coordinates.',
     $ ' ',
     $ '  Keywords are the MONSTA ELLIPROF keywords, e.g.',
     $ '    X0= Y0= R0= R1= NR= RLAW= LINEAR FIXCTR= ELLIP= NITER=',
     $ '    SCALE= SKY= MODEL RMSTAR COS3X= COS4X= TIE= AVG= GAIN=',
     $ '    GC VERBOSE TEST DUMP=',
     $ '  --sky value       subtract a constant sky first (MONSTA SC);',
     $ '                    not the same as the SKY= keyword',
     $ '  --sc value        deprecated alias for --sky',
     $ '  --sky-image file  subtract a sky image first (MONSTA SI)',
     $ '  --mask file       then multiply by a mask (MONSTA MI);',
     $ '                    0 = masked, 1 = good; BITPIX=1 supported',
     $ '  -o out.prf        profile as SAVE ELLIPROF=file ASCII',
     $ '  --csv out.csv     profile as commented fixed-width CSV',
     $ '  --reg out.reg     fitted ellipses as DS9 regions',
     $ '  -m model.fits     the MODEL (or GC model) image',
     $ '  --prepared file   write the image as passed to ELLIPROF',
     $ '                    (after sky and mask), for diagnostics',
     $ '  --prepare-only    stop after writing --prepared (no fit;',
     $ '                    X0/Y0/R0/R1/NR not needed)',
     $ '  --version         print the backend version'
      RETURN
      END
