C     CFITSIO Fortran-interface ABI probe (standalone; no ELLIPROF).
C
C     CFITSIO's Fortran wrappers (f77_wrap*.c, cfortran.h) must know
C     whether a C long is wider than a Fortran INTEGER.  f77_wrap.h
C     decides this from a fixed list of architectures; on one missing
C     from it (riscv64 in CFITSIO 4.7.0) every argument declared long in
C     C is passed with the wrong size: FTGISZ returned 256 x 256 as
C     256, 0 and overwrote the next two array elements; FTGPVE failed
C     with status 307.  This program writes a small image, reads it back
C     through the same calls the ELLIPROF backend uses, and stops with
C     exit status 1 on any wrong size, status, pixel or overwrite.
C
C        gfortran -o probe cfitsio_f77_probe.f libcfitsio.a -lz -lm
C        ./probe            (writes and deletes probe.fits in the cwd)
      PROGRAM PROBE
      INTEGER NX, NY, N
      PARAMETER (NX = 7, NY = 5, N = NX*NY)
      INTEGER IU, ST, NAX, NAXES(4), BS, I, NBAD
      REAL PIX(N), BACK(N+1)
      DOUBLE PRECISION DPIX(N), DBACK(N+1)
      LOGICAL ANYF

      NBAD = 0
      DO 1 I = 1, N
         PIX(I) = REAL(I) + 0.25
         DPIX(I) = DBLE(I) + 0.125D0
 1    CONTINUE

C     ---- write: FTPHPS (long naxes[]), FTPPRE, FTPPRD (long firstelem,
C     nelements)
      ST = 0
      CALL FTGIOU(IU, ST)
      CALL FTINIT(IU, '!probe.fits', 1, ST)
      NAXES(1) = NX
      NAXES(2) = NY
      CALL FTPHPS(IU, -32, 2, NAXES, ST)
      CALL FTPPRE(IU, 1, 1, N, PIX, ST)
      CALL FTCRHD(IU, ST)
      CALL FTPHPS(IU, -64, 2, NAXES, ST)
      CALL FTPPRD(IU, 1, 1, N, DPIX, ST)
      CALL FTCLOS(IU, ST)
      CALL CHECK('write (FTPHPS/FTPPRE/FTPPRD)', ST, 0, NBAD)

C     ---- read the REAL*4 image: FTGIDM, FTGISZ, FTGPVE
      ST = 0
      CALL FTNOPN(IU, 'probe.fits', 0, ST)
      CALL CHECK('FTNOPN', ST, 0, NBAD)
      CALL FTGIDT(IU, BS, ST)
      CALL FTGIDM(IU, NAX, ST)
      CALL CHECK('FTGIDT BITPIX', BS, -32, NBAD)
      CALL CHECK('FTGIDM NAXIS', NAX, 2, NBAD)
      NAXES(1) = -7
      NAXES(2) = -7
      NAXES(3) = -7
      NAXES(4) = -7
      CALL FTGISZ(IU, 2, NAXES, ST)
      WRITE (6,'(A,4I6,A,I0)') ' FTGISZ: NAXES(1:4) =', NAXES,
     $     '  status ', ST
      CALL CHECK('FTGISZ status', ST, 0, NBAD)
      CALL CHECK('FTGISZ NAXIS1', NAXES(1), NX, NBAD)
      CALL CHECK('FTGISZ NAXIS2', NAXES(2), NY, NBAD)
      CALL CHECK('FTGISZ wrote NAXES(3)', NAXES(3), -7, NBAD)
      CALL CHECK('FTGISZ wrote NAXES(4)', NAXES(4), -7, NBAD)
      DO 2 I = 1, N+1
         BACK(I) = -1.0
 2    CONTINUE
      CALL FTGPVE(IU, 1, 1, N, 0.0, BACK, ANYF, ST)
      WRITE (6,'(A,I0,A,2F8.2)') ' FTGPVE: status ', ST,
     $     '  first/last ', BACK(1), BACK(N)
      CALL CHECK('FTGPVE status', ST, 0, NBAD)
      DO 3 I = 1, N
         IF (BACK(I) .NE. PIX(I)) THEN
            CALL CHECK('FTGPVE pixel (index)', I, 0, NBAD)
            GO TO 4
         END IF
 3    CONTINUE
 4    CALL CHECK('FTGPVE wrote past nelements', INT(BACK(N+1)), -1,
     $     NBAD)
C     a first element > 1 (the long firstelem argument itself)
      BACK(1) = -1.0
      CALL FTGPVE(IU, 1, NX+1, 1, 0.0, BACK, ANYF, ST)
      CALL CHECK('FTGPVE firstelem status', ST, 0, NBAD)
      IF (BACK(1) .NE. PIX(NX+1))
     $     CALL CHECK('FTGPVE firstelem pixel', 1, 0, NBAD)

C     ---- read the REAL*8 extension: FTMAHD, FTGPVD
      CALL FTMAHD(IU, 2, BS, ST)
      DO 5 I = 1, N+1
         DBACK(I) = -1.0D0
 5    CONTINUE
      CALL FTGPVD(IU, 1, 1, N, 0.0D0, DBACK, ANYF, ST)
      CALL CHECK('FTGPVD status', ST, 0, NBAD)
      DO 6 I = 1, N
         IF (DBACK(I) .NE. DPIX(I)) THEN
            CALL CHECK('FTGPVD pixel (index)', I, 0, NBAD)
            GO TO 7
         END IF
 6    CONTINUE
 7    CALL CHECK('FTGPVD wrote past nelements', INT(DBACK(N+1)), -1,
     $     NBAD)
      ST = 0
      CALL FTDELT(IU, ST)
      CALL FTFIOU(IU, ST)

      IF (NBAD .NE. 0) THEN
         WRITE (6,'(A,I0,A)') ' CFITSIO Fortran ABI probe: FAILED (',
     $        NBAD, ' check(s)); see tools/ci/build_cfitsio.sh'
         STOP 1
      END IF
      WRITE (6,'(A)') ' CFITSIO Fortran ABI probe: OK'
      END

      SUBROUTINE CHECK(WHAT, GOT, WANT, NBAD)
      CHARACTER*(*) WHAT
      INTEGER GOT, WANT, NBAD
      IF (GOT .NE. WANT) THEN
         WRITE (6,'(3A,I0,A,I0)') ' probe FAILED: ', WHAT, ': got ',
     $        GOT, ', expected ', WANT
         NBAD = NBAD + 1
      END IF
      RETURN
      END
