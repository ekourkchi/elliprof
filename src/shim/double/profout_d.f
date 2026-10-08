C     The CSV table and DS9 regions of the double backend, from /PRFD/
C     (see profout.f for the single ones and the column meanings).

C     DS9 regions: as WRITEREG, from the double profile.
      SUBROUTINE WRITEREGD(FNAME, ISC, ISR, IERR)
      IMPLICIT NONE
      CHARACTER*(*) FNAME
      INTEGER ISC, ISR, IERR
      INCLUDE 'profile_d.inc'
      INTEGER K, NBAD
      DOUBLE PRECISION XC, YC, A, B, ANG

      OPEN (7, FILE=FNAME, FORM='FORMATTED', STATUS='UNKNOWN',
     $     IOSTAT=IERR)
      IF (IERR .NE. 0) THEN
         WRITE (0,'(3A)') 'elliprof: error (double precision, output):'
     $        //' cannot open ', FNAME(1:LEN_TRIM(FNAME))
         RETURN
      END IF
      WRITE (7,'(A)') '# Region file format: DS9 version 4.1',
     $     'global color=green width=1', 'image'
      NBAD = 0
      DO 10 K = 1, N_PRF
         XC = PARAM_PRF(2,K) - ISC + 0.5D0
         YC = PARAM_PRF(3,K) - ISR + 0.5D0
         A = PARAM_PRF(1,K)
         B = PARAM_PRF(1,K) * (1 - PARAM_PRF(6,K))
         ANG = PARAM_PRF(5,K) - 90
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
      IF (NBAD .GT. 0) WRITE (0,'(A,I0,2A)') 'elliprof: ', NBAD,
     $     ' contour(s) with NaN left out of ', FNAME(1:LEN_TRIM(FNAME))
      RETURN
      END

C     The CSV table: the columns of WRITECSV, every value as ES25.17E3
C     (18 significant digits, explicit 3-digit exponent: the whole
C     double range, read back exactly), and more comment lines for the
C     precision (PRECLN), the normalization (NORMLN) and, with a model,
C     the model pixels that underflowed to zero (UNDLN).
      SUBROUTINE WRITECSVD(FNAME, IMAGE, MASK, SKY, PARAMS, ISC, ISR,
     $     PRECLN, NORMLN, UNDLN, SUBLN, IERR)
      IMPLICIT NONE
      CHARACTER*(*) FNAME, IMAGE, MASK, SKY, PARAMS, PRECLN, NORMLN
      CHARACTER*(*) UNDLN, SUBLN
      INTEGER ISC, ISR, IERR
      INCLUDE 'profile_d.inc'
      INCLUDE 'version.inc'
      INTEGER K, J

      OPEN (7, FILE=FNAME, FORM='FORMATTED', STATUS='UNKNOWN',
     $     IOSTAT=IERR)
      IF (IERR .NE. 0) THEN
         WRITE (0,'(3A)') 'elliprof: error (double precision, output):'
     $        //' cannot open ', FNAME(1:LEN_TRIM(FNAME))
         RETURN
      END IF
      WRITE (7,'(A)') '# ELLIPROF surface photometry profile',
     $     '# Input: '//IMAGE(1:LEN_TRIM(IMAGE)),
     $     '# Mask: '//MASK(1:LEN_TRIM(MASK)),
     $     '# Sky: '//SKY(1:LEN_TRIM(SKY)),
     $     '# Parameters: '//PARAMS(1:LEN_TRIM(PARAMS)),
     $     '# elliprof version: '//VERSTR,
     $     '# Precision: '//PRECLN(1:LEN_TRIM(PRECLN)),
     $     '# Normalization: '//NORMLN(1:LEN_TRIM(NORMLN))
      IF (UNDLN .NE. ' ') WRITE (7,'(A)')
     $     '# Model underflow to zero: '//UNDLN(1:LEN_TRIM(UNDLN))
      IF (SUBLN .NE. ' ') WRITE (7,'(A)')
     $     '# Model subnormal (nonzero): '//SUBLN(1:LEN_TRIM(SUBLN))
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
     $ 'from +x'
      IF (PARAM_PRF(12,15) .LT. 0) WRITE (7,'(A)')
     $ '# Harmonic order: 6 (COS3X < 0): I3 = 6th-order amplitude, '//
     $ 'A3 = 2 x 6th-order phase (deg); there is no 3rd-order term'
      WRITE (7,'(A)') '#'
      WRITE (7,1002) '#', 'Rmaj', 'x0', 'y0', 'I0', 'alpha', 'ellip',
     $     'I3', 'A3', 'I4', 'A4', 'slope'
 1002 FORMAT (A1,A24,10(', ',A25))
      DO 10 K = 1, N_PRF
         WRITE (7,1003) (PARAM_PRF(J,K),J=1,11)
 10   CONTINUE
 1003 FORMAT (ES25.17E3,10(', ',ES25.17E3))
      CLOSE (7)
      RETURN
      END
