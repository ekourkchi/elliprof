C     Write a noiseless synthetic r^(1/4) elliptical galaxy as a FITS
C     image, for checking that the standalone ELLIPROF runs.  This is
C     a smoke test only, not evidence of scientific equivalence.
C
C     Coordinates follow ELLIPROF: the centre of pixel DATA(IX,IY) is
C     at (x,y) = (IX-0.5, IY-0.5), and the position angle ALPHA is
C     measured counter-clockwise from the +x (column) axis.
C
C     Usage: mktestimage out.fits

      PROGRAM MKTESTIMAGE
      PARAMETER (NX=256, NY=256)
      PARAMETER (X0=127.3, Y0=121.6, RE=20.0, FE=200.0)
      PARAMETER (Q=0.7, ALPHADEG=30.0, SKY=100.0)
      REAL PIX(NX,NY)
      INTEGER STATUS, IUNIT, NAXES(2)
      CHARACTER*256 FNAME

      CALL GET_COMMAND_ARGUMENT(1, FNAME)
      IF (FNAME .EQ. ' ') FNAME = 'test_image.fits'

      CA = COS(ALPHADEG*3.14159265/180)
      SA = SIN(ALPHADEG*3.14159265/180)
      DO 10 IY = 1, NY
         DO 11 IX = 1, NX
            DX = (IX-0.5) - X0
            DY = (IY-0.5) - Y0
            U = DX*CA + DY*SA
            V = -DX*SA + DY*CA
            R = SQRT(U*U + (V/Q)*(V/Q))
            PIX(IX,IY) = FE*EXP(-7.669*(SQRT(SQRT(R/RE)) - 1)) + SKY
 11      CONTINUE
 10   CONTINUE

      STATUS = 0
      CALL FTGIOU(IUNIT, STATUS)
      CALL FTINIT(IUNIT, '!'//FNAME(1:LEN_TRIM(FNAME)), 1, STATUS)
      NAXES(1) = NX
      NAXES(2) = NY
      CALL FTPHPS(IUNIT, -32, 2, NAXES, STATUS)
      CALL FTPKYE(IUNIT, 'TX0', X0, 6, 'true centre x (ELLIPROF X0)',
     $     STATUS)
      CALL FTPKYE(IUNIT, 'TY0', Y0, 6, 'true centre y (ELLIPROF Y0)',
     $     STATUS)
      CALL FTPKYE(IUNIT, 'TRE', RE, 6, 'true effective radius, pix',
     $     STATUS)
      CALL FTPKYE(IUNIT, 'TIE', FE, 6, 'true I(Re) above sky', STATUS)
      CALL FTPKYE(IUNIT, 'TELLIP', 1-Q, 6, 'true ellipticity 1-b/a',
     $     STATUS)
      CALL FTPKYE(IUNIT, 'TALPHA', ALPHADEG, 6,
     $     'true PA, deg CCW from +x', STATUS)
      CALL FTPKYE(IUNIT, 'TSKY', SKY, 6, 'true sky', STATUS)
      CALL FTPHIS(IUNIT,
     $     'Synthetic r^1/4 galaxy for ELLIPROF smoke test', STATUS)
      CALL FTPPRE(IUNIT, 1, 1, NX*NY, PIX, STATUS)
      CALL FTCLOS(IUNIT, STATUS)
      CALL FTFIOU(IUNIT, STATUS)
      IF (STATUS .NE. 0) THEN
         WRITE (0,*) 'mktestimage: CFITSIO status', STATUS
         STOP 1
      END IF
      WRITE (6,*) 'wrote ', FNAME(1:LEN_TRIM(FNAME))
      END
