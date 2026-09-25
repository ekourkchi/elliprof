C     Standalone driver for the MONSTA/VISTA ELLIPROF command.
C
C     This replaces only the parts of VISTA that normally run around
C     ELLIPROF: reading the image (RD), splitting the command line
C     into WORD() the way vista.f does, setting GO/XERR/NOGO and the
C     image origin ISR/ISC, and printing the result the way
C     PRINT EPROF and SAVE ELLIPROF=file ASCII do.  ELLIPROF and
C     everything it calls are compiled unchanged from src/original.
C
C     Before ELLIPROF the image can be prepared the way the SBF
C     pipeline's MONSTA scripts do it:  SC 1 sky  (--sc), then
C     RD 2 mask / MI 1 2  (--mask).  ELLIPROF has no mask input of its
C     own; it skips pixels that are exactly 0, which MI leaves in the
C     masked areas.
C
C     Usage:  elliprof image.fits [KEY=value ...] [--sc sky]
C                     [--mask mask] [-o out.prf] [-m model.fits]
C                     [--csv out.csv] [--reg out.reg]

      PROGRAM ELLIPROFMAIN
      INCLUDE 'vistalink.inc'
      INCLUDE 'imagelink.inc'
      INCLUDE 'profile.inc'

      REAL, ALLOCATABLE :: PIX(:,:), MPIX(:,:)
      CHARACTER*1024 ARG, FITSFILE, PRFFILE, MODFILE, CSVFILE, REGFILE
      CHARACTER*1024 MASKFILE, PREP
      CHARACTER*289 OSTRNG, LCSTRNG, SCSTR
      LOGICAL ERR, DOMODEL, DOGC, DOSC
      INTEGER UPPER, NARGS, IARG, IWORD, JCHAR, IB, ICON
      INTEGER NTYPE, NUM, NCHAR, NCOL, NROW, IUNIT, IERR, L, I, J
      INTEGER ICOS3X, MBITPIX, MCOL, MROW, MSC, MSR, IOFF
      INTEGER NZERO, NOTHER
      REAL FNUM, SCVAL

C     ---- Command line: image file, driver options, ELLIPROF words

      NARGS = COMMAND_ARGUMENT_COUNT()
      FITSFILE = ' '
      PRFFILE = ' '
      MODFILE = ' '
      CSVFILE = ' '
      REGFILE = ' '
      MASKFILE = ' '
      SCSTR = ' '
      COMMAND = 'ELLIPROF'
      IARG = 0
 10   IARG = IARG + 1
      IF (IARG .GT. NARGS) GOTO 20
      CALL GET_COMMAND_ARGUMENT(IARG, ARG)
      IF (ARG .EQ. '-h' .OR. ARG .EQ. '--help') THEN
         CALL USAGE
         STOP
      ELSE IF (ARG .EQ. '-o' .OR. ARG .EQ. '-m' .OR.
     $        ARG .EQ. '--csv' .OR. ARG .EQ. '--reg' .OR.
     $        ARG .EQ. '--mask' .OR. ARG .EQ. '--sc') THEN
         IF (IARG .EQ. NARGS) THEN
            WRITE (0,*) 'elliprof: ', ARG(1:LEN_TRIM(ARG)),
     $           ' needs a value'
            STOP 1
         END IF
         IARG = IARG + 1
         IF (ARG .EQ. '-o') THEN
            CALL GET_COMMAND_ARGUMENT(IARG, PRFFILE)
         ELSE IF (ARG .EQ. '-m') THEN
            CALL GET_COMMAND_ARGUMENT(IARG, MODFILE)
         ELSE IF (ARG .EQ. '--csv') THEN
            CALL GET_COMMAND_ARGUMENT(IARG, CSVFILE)
         ELSE IF (ARG .EQ. '--mask') THEN
            CALL GET_COMMAND_ARGUMENT(IARG, MASKFILE)
         ELSE IF (ARG .EQ. '--sc') THEN
            CALL GET_COMMAND_ARGUMENT(IARG, SCSTR)
         ELSE
            CALL GET_COMMAND_ARGUMENT(IARG, REGFILE)
         END IF
      ELSE IF (FITSFILE .EQ. ' ') THEN
         FITSFILE = ARG
      ELSE
         L = LEN_TRIM(COMMAND)
         IF (L + 1 + LEN_TRIM(ARG) .GT. LEN(COMMAND)) THEN
            WRITE (0,*) 'elliprof: command line longer than',
     $           LEN(COMMAND), ' characters'
            STOP 1
         END IF
         COMMAND = COMMAND(1:L) // ' ' // ARG
      END IF
      GOTO 10

 20   IF (FITSFILE .EQ. ' ') THEN
         CALL USAGE
         STOP 1
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
      DO 45 I = 1, NCON
         IF (WORD(I) .EQ. 'MODEL') DOMODEL = .TRUE.
         IF (WORD(I) .EQ. 'GC') DOGC = .TRUE.
 45   CONTINUE

C     ---- VISTA control flags

      GO = .TRUE.
      CHECK = .TRUE.
      XERR = .FALSE.
      NOGO = .FALSE.
      XEOF = .FALSE.
      MONSTA = 1
      TTYLUN = 6
      REDIRLUN = 6

C     ---- --sc value, parsed by DISSECT as VISTA parses "SC 1 value":
C     a float goes through CONST (REAL*4), an integer through
C     FLOAT(IBUF) (arith.f)

      DOSC = SCSTR .NE. ' '
      IF (DOSC) THEN
         L = UPPER(SCSTR)
         CALL DISSECT(SCSTR, 1, .FALSE., NTYPE, NUM, FNUM, OSTRNG,
     $        NCHAR, ERR)
         IF (ERR .OR. NTYPE .EQ. 3) THEN
            WRITE (0,*) 'elliprof: --sc needs a number, got ',
     $           SCSTR(1:LEN_TRIM(SCSTR))
            STOP 1
         END IF
         IF (NTYPE .EQ. 1) THEN
            SCVAL = FLOAT(NUM)
         ELSE
            SCVAL = FNUM
         END IF
      END IF

C     ---- Read the image into buffer 1 (what RD 1 file does)

      CALL FITSOPENIM(FITSFILE, IUNIT, NCOL, NROW, ISC, ISR,
     $     HEADBUF(1), IERR)
      IF (IERR .NE. 0) STOP 1
      ALLOCATE (PIX(NCOL,NROW))
      CALL FITSREADPIX(IUNIT, NCOL, NROW, PIX, IERR)
      IF (IERR .NE. 0) STOP 1

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

C     ---- SC 1 value: A = A + (-F) in REAL*4, as ARITHCON does.
C     This must come before the mask, so masked pixels end up at 0.

      PREP = ' '
      IF (DOSC) THEN
         FNUM = -SCVAL
         DO 60 J = 1, NROW
            DO 61 I = 1, NCOL
               PIX(I,J) = PIX(I,J) + FNUM
 61         CONTINUE
 60      CONTINUE
         WRITE (6,1001) SCVAL
 1001    FORMAT (' SC: subtracted',1PG16.8,' from every pixel')
         WRITE (PREP,'(A,G0)') 'SC ', SCVAL
      END IF

C     ---- RD 2 mask / MI 1 2: A = A * B.  Unlike MONSTA, which only
C     multiplies where the two images overlap, insist that the mask
C     matches the image exactly.

      IF (MASKFILE .NE. ' ') THEN
         CALL MASKHEAD(MASKFILE, MBITPIX, MCOL, MROW, MSC, MSR, IOFF,
     $        IERR)
         IF (IERR .NE. 0) STOP 1
         IF (MCOL .NE. NCOL .OR. MROW .NE. NROW .OR.
     $        MSC .NE. ISC .OR. MSR .NE. ISR) THEN
            WRITE (0,1002) MASKFILE(1:LEN_TRIM(MASKFILE)), MCOL, MROW,
     $           MSC, MSR, NCOL, NROW, ISC, ISR
 1002       FORMAT (' elliprof: mask ',A,' is ',I0,' x ',I0,
     $           ' with origin (',I0,',',I0,') but the image is ',
     $           I0,' x ',I0,' with origin (',I0,',',I0,')')
            STOP 1
         END IF
         ALLOCATE (MPIX(NCOL,NROW))
         CALL MASKREAD(MASKFILE, MBITPIX, IOFF, NCOL, NROW, MPIX, IERR)
         IF (IERR .NE. 0) STOP 1
         NZERO = 0
         NOTHER = 0
         DO 70 J = 1, NROW
            DO 71 I = 1, NCOL
               IF (MPIX(I,J) .EQ. 0.0) THEN
                  NZERO = NZERO + 1
               ELSE IF (MPIX(I,J) .NE. 1.0) THEN
                  NOTHER = NOTHER + 1
               END IF
               PIX(I,J) = PIX(I,J) * MPIX(I,J)
 71         CONTINUE
 70      CONTINUE
         WRITE (6,1003) MASKFILE(1:LEN_TRIM(MASKFILE)), MBITPIX,
     $        NZERO, 100.0*NZERO/(FLOAT(NCOL)*NROW)
 1003    FORMAT (' MI: mask ',A,' (BITPIX ',I0,'): ',I0,
     $        ' pixels masked (',F6.3,'%)')
         IF (NOTHER .GT. 0) WRITE (0,*) 'elliprof: ', NOTHER,
     $        ' mask pixels are neither 0 nor 1; MI multiplies by them'
         DEALLOCATE (MPIX)
         L = LEN_TRIM(PREP)
         IF (L .GT. 0) THEN
            PREP = PREP(1:L) // ' then MI by mask ' // MASKFILE
         ELSE
            PREP = 'MI by mask ' // MASKFILE
         END IF
      END IF

C     ---- Run the unchanged ELLIPROF

      CALL ELLIPROF(PIX, NROW, NCOL)
      IF (DOMODEL) WRITE (0,*)

      IF (XERR) THEN
         WRITE (0,*) 'elliprof: ELLIPROF reported an error'
         STOP 1
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
         STOP 1
      END IF

C     ---- Save the profile the way SAVE ELLIPROF=file ASCII does

      IF (PRFFILE .NE. ' ') THEN
         IF (N_PRF .GT. 0) THEN
            OPEN (4, FILE=PRFFILE, FORM='FORMATTED', STATUS='UNKNOWN',
     $           IOSTAT=IERR)
            IF (IERR .NE. 0) THEN
               WRITE (0,*) 'elliprof: cannot open ',
     $              PRFFILE(1:LEN_TRIM(PRFFILE))
               STOP 1
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
               CALL WRITECSV(CSVFILE, FITSFILE, PREP, ISC, ISR, IERR)
               IF (IERR .NE. 0) STOP 1
            END IF
            IF (REGFILE .NE. ' ') THEN
               CALL WRITEREG(REGFILE, ISC, ISR, IERR)
               IF (IERR .NE. 0) STOP 1
            END IF
         ELSE
            WRITE (0,*) 'elliprof: --csv/--reg ignored,',
     $           ' GC mode has no profile'
         END IF
      END IF

C     ---- Write the model image, which ELLIPROF left in PIX

      IF (MODFILE .NE. ' ') THEN
         IF (DOMODEL) THEN
            CALL FITSWRITEIM(MODFILE, NCOL, NROW, PIX, ISC, ISR, IERR)
            IF (IERR .NE. 0) STOP 1
         ELSE
            WRITE (0,*) 'elliprof: -m ignored, MODEL was not given'
         END IF
      ELSE IF (DOMODEL) THEN
         WRITE (0,*) 'elliprof: MODEL given without -m file;',
     $        ' model image not saved'
      END IF

      END

      SUBROUTINE USAGE
      WRITE (0,'(A)')
     $ 'usage: elliprof image.fits [KEY=value ...] [--sc sky]',
     $ '         [--mask mask] [-o out.prf] [-m model.fits]',
     $ '         [--csv out.csv] [--reg out.reg]',
     $ ' ',
     $ '  Keywords are the MONSTA ELLIPROF keywords, e.g.',
     $ '    X0= Y0= R0= R1= NR= RLAW= LINEAR FIXCTR= ELLIP= NITER=',
     $ '    SCALE= SKY= MODEL RMSTAR COS3X= COS4X= TIE= AVG= GAIN=',
     $ '    GC VERBOSE TEST DUMP= EDIT',
     $ '  --sc sky       subtract sky first, as MONSTA SC 1 sky',
     $ '                 (not the same as the SKY= keyword)',
     $ '  --mask mask    then multiply by mask (MONSTA RD + MI);',
     $ '                 0 = masked, 1 = good; BITPIX=1 supported',
     $ '  -o out.prf     save profile as SAVE ELLIPROF=file ASCII',
     $ '  -m model.fits  write the MODEL (or GC model) image',
     $ '  --csv out.csv  profile as commented, fixed-width CSV',
     $ '  --reg out.reg  fitted ellipses as a DS9 region file'
      RETURN
      END
