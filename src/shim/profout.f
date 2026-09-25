C     Extra, human-oriented outputs made from the final /PRF/ contents
C     after ELLIPROF returns.  PARAM_PRF(J,K) for contour K, as filled
C     at the end of ELLIPROF (elliprof.f, loop 30) and printed by
C     the original profile printout (the comments in profile.inc are
C     out of date):
C        1 Rmaj   2 x0 (+ISC)   3 y0 (+ISR)   4 I0
C        5 alpha  (ELLIPROF internal PA, CCW from +x, minus 90 deg)
C        6 ellip  (1 - b/a)
C        7 I3   8 A3   9 I4   10 A4   11 slope (d log I / d log r)
C     Row 12 holds ELLIPROF's run flags, not a contour value.

C     DS9 region file, one ellipse per contour, image coordinates.
C     ELLIPROF puts the centre of DATA(ix,iy) at ix-0.5, DS9 at ix,
C     and x0/y0 include the CNPIX origin, so the DS9 centre is
C     x0 - ISC + 0.5, y0 - ISR + 0.5.  The DS9 angle is alpha - 90
C     (the major axis is at alpha + 90; the two differ by 180 deg).
      SUBROUTINE WRITEREG(FNAME, ISC, ISR, IERR)
      CHARACTER*(*) FNAME
      INTEGER ISC, ISR, IERR
      INCLUDE 'profile.inc'
      INTEGER K, NBAD
      REAL XC, YC, A, B, ANG

      OPEN (7, FILE=FNAME, FORM='FORMATTED', STATUS='UNKNOWN',
     $     IOSTAT=IERR)
      IF (IERR .NE. 0) THEN
         WRITE (0,*) 'elliprof: cannot open ', FNAME(1:LEN_TRIM(FNAME))
         RETURN
      END IF
      WRITE (7,'(A)') '# Region file format: DS9 version 4.1',
     $     'global color=green width=1', 'image'
      NBAD = 0
      DO 10 K = 1, N_PRF
         XC = PARAM_PRF(2,K) - ISC + 0.5
         YC = PARAM_PRF(3,K) - ISR + 0.5
         A = PARAM_PRF(1,K)
         B = PARAM_PRF(1,K) * (1 - PARAM_PRF(6,K))
         ANG = PARAM_PRF(5,K) - 90
C     NaN compares unequal to itself; DS9 cannot parse such a line
         IF (XC.NE.XC .OR. YC.NE.YC .OR. A.NE.A .OR. B.NE.B .OR.
     $        ANG.NE.ANG) THEN
            NBAD = NBAD + 1
            WRITE (7,'(A,I4,A)') '# contour', K, ' skipped: NaN'
         ELSE
            WRITE (7,1000) XC, YC, A, B, ANG
         END IF
 10   CONTINUE
 1000 FORMAT ('ellipse(',F0.4,',',F0.4,',',F0.4,',',F0.4,',',F0.4,')')
      CLOSE (7)
      IF (NBAD .GT. 0) WRITE (0,*) 'elliprof: ', NBAD,
     $     ' contour(s) with NaN left out of ', FNAME(1:LEN_TRIM(FNAME))
      RETURN
      END

C     Comma-separated profile with fixed-width columns and # comments.
C     Values are PARAM_PRF exactly as stored.  PARAMS is the ELLIPROF
C     keyword line, recorded for provenance.
C     MASK and SKY describe the preparation ('none' if not used).
      SUBROUTINE WRITECSV(FNAME, IMAGE, MASK, SKY, PARAMS, ISC, ISR,
     $     IERR)
      CHARACTER*(*) FNAME, IMAGE, MASK, SKY, PARAMS
      INTEGER ISC, ISR, IERR
      INCLUDE 'profile.inc'
      INCLUDE 'version.inc'
      INTEGER K, J

      OPEN (7, FILE=FNAME, FORM='FORMATTED', STATUS='UNKNOWN',
     $     IOSTAT=IERR)
      IF (IERR .NE. 0) THEN
         WRITE (0,*) 'elliprof: cannot open ', FNAME(1:LEN_TRIM(FNAME))
         RETURN
      END IF
      WRITE (7,'(A)') '# ELLIPROF surface photometry profile',
     $     '# Input: '//IMAGE(1:LEN_TRIM(IMAGE)),
     $     '# Mask: '//MASK(1:LEN_TRIM(MASK)),
     $     '# Sky: '//SKY(1:LEN_TRIM(SKY)),
     $     '# Parameters: '//PARAMS(1:LEN_TRIM(PARAMS)),
     $     '# elliprof version: '//VERSTR
      WRITE (7,1001) N_PRF, PRF_SC, ISC, ISR
 1001 FORMAT ('# Contours: ',I0,'   SCALE: ',G0,
     $     '   Image origin (CNPIX1,CNPIX2): ',I0,',',I0)
      WRITE (7,'(A)') '# Columns:',
     $ '# Rmaj, x0, y0, I0, alpha, ellip, I3, A3, I4, A4, slope',
     $ '# Units: Rmaj,x0,y0=pixels; alpha,A3,A4=degrees;'//
     $ ' I0=image units; I3,I4=amplitude relative to I0;'//
     $ ' slope=dlogI/dlogr',
     $ '# x0,y0: ELLIPROF image coordinates, centre of pixel ix at '//
     $ 'ix-0.5,'//
     $ ' plus image origin (DS9 image x = x0 - CNPIX1 + 0.5)',
     $ '# alpha: position angle; major axis at alpha+90 deg CCW '//
     $ 'from +x',
     $ '#'
      WRITE (7,1002) '#', 'Rmaj', 'x0', 'y0', 'I0', 'alpha', 'ellip',
     $     'I3', 'A3', 'I4', 'A4', 'slope'
 1002 FORMAT (A1,A9,', ',A10,', ',A10,', ',A15,', ',A10,', ',A10,
     $     ', ',A15,', ',A10,', ',A15,', ',A10,', ',A10)
      DO 10 K = 1, N_PRF
         WRITE (7,1003) (PARAM_PRF(J,K),J=1,11)
 10   CONTINUE
 1003 FORMAT (F10.4,', ',F10.4,', ',F10.4,', ',ES15.7,', ',F10.4,
     $     ', ',F10.6,', ',ES15.7,', ',F10.4,', ',ES15.7,', ',F10.4,
     $     ', ',F10.6)
      CLOSE (7)
      RETURN
      END
