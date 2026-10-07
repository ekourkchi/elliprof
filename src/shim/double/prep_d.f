C     Image preparation for the double backend (see prep.f for the
C     single one; the order and the rules are the same):
C
C        --sky V        A = A - V
C        --sky-image F  A = A - B
C        --mask F       A = 0 where the mask is bad, else unchanged
C
C     All in DOUBLE PRECISION (IEEE-754 binary64).  The science and sky
C     images are read by CFITSIO in double (BSCALE/BZERO applied in
C     double), so no value passes through REAL*4.  Then the
C     normalization: the image handed to ELLIPROFD is the prepared one
C     times 2**(-K), an exact power of two (NORMEXPD).

C     One plain number, parsed exactly: an optional sign, digits with an
C     optional decimal point, an optional exponent (E or D).  Converted
C     by the Fortran run time, i.e. correctly rounded to the nearest
C     double.  IERR = 0 ok, 1 not a plain number, 2 beyond the double
C     range (would be Inf), 3 nonzero but below the smallest double
C     (would be 0).  NaN and Inf are never accepted.
      SUBROUTINE PARSENUMD(STR, VAL, IERR)
      IMPLICIT NONE
      CHARACTER*(*) STR
      DOUBLE PRECISION VAL
      INTEGER IERR
      INTEGER I, I0, I1, NDIG, NEXP, IOS
      LOGICAL NONZERO
      CHARACTER C

      IERR = 1
      VAL = 0
      I1 = LEN_TRIM(STR)
      I0 = 1
 5    IF (I0 .LE. I1) THEN
         IF (STR(I0:I0) .EQ. ' ') THEN
            I0 = I0 + 1
            GOTO 5
         END IF
      END IF
      IF (I0 .GT. I1) RETURN
      I = I0
      IF (STR(I:I) .EQ. '+' .OR. STR(I:I) .EQ. '-') I = I + 1
      NDIG = 0
      NONZERO = .FALSE.
 10   IF (I .LE. I1) THEN
         C = STR(I:I)
         IF (C .GE. '0' .AND. C .LE. '9') THEN
            NDIG = NDIG + 1
            IF (C .NE. '0') NONZERO = .TRUE.
            I = I + 1
            GOTO 10
         END IF
      END IF
      IF (I .LE. I1) THEN
         IF (STR(I:I) .EQ. '.') THEN
            I = I + 1
 20         IF (I .LE. I1) THEN
               C = STR(I:I)
               IF (C .GE. '0' .AND. C .LE. '9') THEN
                  NDIG = NDIG + 1
                  IF (C .NE. '0') NONZERO = .TRUE.
                  I = I + 1
                  GOTO 20
               END IF
            END IF
         END IF
      END IF
      IF (NDIG .EQ. 0) RETURN
      IF (I .LE. I1) THEN
         C = STR(I:I)
         IF (C .NE. 'E' .AND. C .NE. 'e' .AND. C .NE. 'D' .AND.
     $        C .NE. 'd') RETURN
         I = I + 1
         IF (I .LE. I1) THEN
            IF (STR(I:I) .EQ. '+' .OR. STR(I:I) .EQ. '-') I = I + 1
         END IF
         NEXP = 0
 30      IF (I .LE. I1) THEN
            C = STR(I:I)
            IF (C .GE. '0' .AND. C .LE. '9') THEN
               NEXP = NEXP + 1
               I = I + 1
               GOTO 30
            END IF
         END IF
         IF (NEXP .EQ. 0) RETURN
      END IF
      IF (I .LE. I1) RETURN
      READ (STR(I0:I1), *, IOSTAT=IOS) VAL
      IF (IOS .NE. 0) RETURN
      IF (ABS(VAL) .GT. HUGE(VAL)) THEN
         IERR = 2
      ELSE IF (VAL .EQ. 0 .AND. NONZERO) THEN
         IERR = 3
      ELSE
         IERR = 0
      END IF
      RETURN
      END

C     The keyword evaluator of ELLIPROFD (in place of ASSIGNd): KEY=V
C     with V a plain number is converted exactly (PARSENUMD); anything
C     else (an expression of the original command language) is left to
C     the original ASSIGNd.  PARM receives the keyword name.
      SUBROUTINE KWVALD(EQUALITY, VAL, PARM)
      CHARACTER*(*) EQUALITY, PARM
      DOUBLE PRECISION VAL
      INCLUDE 'vistalink.inc'
      INTEGER IEQ, IERR, L
      IEQ = INDEX(EQUALITY, '=')
      IF (IEQ .GT. 1) THEN
         CALL PARSENUMD(EQUALITY(IEQ+1:), VAL, IERR)
         IF (IERR .EQ. 0) THEN
            PARM = EQUALITY(1:IEQ-1)
            RETURN
         ELSE IF (IERR .GE. 2) THEN
            L = LEN_TRIM(EQUALITY)
            WRITE (0,'(3A)') 'elliprof: error (double precision, '
     $           //'keywords): ', EQUALITY(1:L),
     $           ' is outside the range of double precision'
            XERR = .TRUE.
            RETURN
         END IF
      END IF
      CALL ASSIGND(EQUALITY, VAL, PARM)
      RETURN
      END

C     X * 2**K, exactly when the result is a normal number (SCALE).
      DOUBLE PRECISION FUNCTION POW2D(X, K)
      IMPLICIT NONE
      DOUBLE PRECISION X
      INTEGER K
      POW2D = SCALE(X, K)
      RETURN
      END

C     True for a finite double (not NaN, not +-Inf).
      LOGICAL FUNCTION FINITED(X)
      IMPLICIT NONE
      DOUBLE PRECISION X
      FINITED = X .EQ. X .AND. ABS(X) .LE. HUGE(X)
      RETURN
      END

C     --sky V.  NOVER counts pixels whose finite value minus V is not
C     finite (overflow beyond the double range).
      SUBROUTINE SUBSKYD(PIX, NCOL, NROW, SKY, NOVER)
      IMPLICIT NONE
      INTEGER NCOL, NROW, I, J, NOVER
      DOUBLE PRECISION PIX(NCOL,NROW), SKY, V
      LOGICAL FINITED
      NOVER = 0
      DO 10 J = 1, NROW
         DO 11 I = 1, NCOL
            V = PIX(I,J)
            PIX(I,J) = V - SKY
            IF (FINITED(V) .AND. .NOT. FINITED(PIX(I,J)))
     $           NOVER = NOVER + 1
 11      CONTINUE
 10   CONTINUE
      RETURN
      END

C     --sky-image F, read in double (FTGPVD) and subtracted pixel by
C     pixel; NOVER as in SUBSKYD (both values finite, the difference
C     not).  Allocation failure: IERR = 2.
      SUBROUTINE SUBSKYIMGD(FNAME, PIX, NCOL, NROW, ISC, ISR, NOVER,
     $     IERR)
      IMPLICIT NONE
      CHARACTER*(*) FNAME
      INTEGER NCOL, NROW, ISC, ISR, NOVER, IERR
      DOUBLE PRECISION PIX(NCOL,NROW), V
      DOUBLE PRECISION, ALLOCATABLE :: B(:,:)
      INTEGER IUNIT, BCOL, BROW, BSC, BSR, I, J, IST
      LOGICAL FINITED
      CHARACTER*81840 HTMP

      NOVER = 0
      CALL FITSOPENIM(FNAME, IUNIT, BCOL, BROW, BSC, BSR, HTMP, IERR)
      IF (IERR .NE. 0) RETURN
      CALL CHKGEOM('sky image', BCOL, BROW, BSC, BSR,
     $     NCOL, NROW, ISC, ISR, IERR)
      IF (IERR .NE. 0) THEN
         CALL FITSCLOSE(IUNIT)
         RETURN
      END IF
      ALLOCATE (B(NCOL,NROW), STAT=IST)
      IF (IST .NE. 0) THEN
         CALL FITSCLOSE(IUNIT)
         CALL NOMEMD('the sky image', 8D0*NCOL*NROW)
         IERR = 2
         RETURN
      END IF
      CALL FITSREADPIXD(IUNIT, NCOL, NROW, B, IERR)
      IF (IERR .EQ. 0) THEN
         DO 10 J = 1, NROW
            DO 11 I = 1, NCOL
               V = PIX(I,J)
               PIX(I,J) = V - B(I,J)
               IF (FINITED(V) .AND. FINITED(B(I,J)) .AND.
     $              .NOT. FINITED(PIX(I,J))) NOVER = NOVER + 1
 11         CONTINUE
 10      CONTINUE
      END IF
      DEALLOCATE (B)
      RETURN
      END

C     --mask F: as APPLYMASK (prep.f), on a double image.  The mask is
C     read by MASKGOOD, already in double, exactly as for single.
      SUBROUTINE APPLYMASKD(FNAME, PIX, NCOL, NROW, ISC, ISR, ZGOOD,
     $     GOOD, MBITPIX, NBAD, NNONF, IERR)
      IMPLICIT NONE
      CHARACTER*(*) FNAME
      INTEGER NCOL, NROW, ISC, ISR, MBITPIX, NBAD, NNONF, IERR
      DOUBLE PRECISION PIX(NCOL,NROW)
      LOGICAL ZGOOD, GOOD(NCOL,NROW)
      INTEGER I, J

      CALL CHKMASK(FNAME, NCOL, NROW, ISC, ISR, IERR)
      IF (IERR .NE. 0) RETURN
      CALL MASKGOOD(FNAME, NCOL, NROW, ZGOOD, GOOD, MBITPIX, NBAD,
     $     NNONF, IERR)
      IF (IERR .NE. 0) RETURN
      DO 10 J = 1, NROW
         DO 11 I = 1, NCOL
            IF (.NOT. GOOD(I,J)) PIX(I,J) = 0
 11      CONTINUE
 10   CONTINUE
      RETURN
      END

C     The normalization exponent.  Statistics over the finite nonzero
C     pixels of the prepared image (masked pixels are exactly 0 and so
C     never count), from a histogram of their binary exponents, so
C     exact and in one pass:
C
C       KPREF  the preferred exponent: EXPONENT of the (lower) median
C              |value| (log fits), or of the largest |value| (LINEAR),
C              so that internal values are near 1, or below 1 in
C              LINEAR (squares, variances and weights stay in range,
C              and no value can reach ELLIPROF's sentinels -1e5, -9e9,
C              -1e10);
C       KMIN   the smallest K for which no value overflows:
C              EXPONENT(max) - MAXEXPONENT;
C       KMAX   the largest K for which no value becomes zero:
C              EXPONENT(min) - (MINEXPONENT - DIGITS) - 1, i.e. the
C              smallest value stays at least the smallest subnormal;
C       K      KPREF clamped into [KMIN, KMAX] (always possible: 0 is
C              in it);
C       NINEX  how many values lose bits (become subnormal internally
C              and are rounded); 0 means the scaling is exact and
C              reversible.
C
C     NUSED = number of finite nonzero pixels; with none, K = 0.
      SUBROUTINE NORMEXPD(PIX, NPIX, LINEAR, KPREF, KMIN, KMAX, K,
     $     NINEX, NUSED)
      IMPLICIT NONE
      INTEGER*8 NPIX, NUSED, NINEX, I, M, NCUM
      DOUBLE PRECISION PIX(NPIX), V, W
      LOGICAL LINEAR, FINITED
      INTEGER KPREF, KMIN, KMAX, K, E, EMIN, EMAX, LO, HI
      PARAMETER (LO = -1100, HI = 1100)
      INTEGER*8 HIST(LO:HI)

      DO 5 E = LO, HI
         HIST(E) = 0
 5    CONTINUE
      NUSED = 0
      EMIN = HI
      EMAX = LO
      DO 10 I = 1, NPIX
         V = PIX(I)
         IF (V .NE. 0 .AND. FINITED(V)) THEN
            E = EXPONENT(V)
            HIST(E) = HIST(E) + 1
            NUSED = NUSED + 1
            IF (E .LT. EMIN) EMIN = E
            IF (E .GT. EMAX) EMAX = E
         END IF
 10   CONTINUE
      NINEX = 0
      IF (NUSED .EQ. 0) THEN
         KPREF = 0
         KMIN = 0
         KMAX = 0
         K = 0
         RETURN
      END IF
      IF (LINEAR) THEN
         KPREF = EMAX
      ELSE
         M = (NUSED + 1) / 2
         NCUM = 0
         DO 20 E = EMIN, EMAX
            NCUM = NCUM + HIST(E)
            IF (NCUM .GE. M) THEN
               KPREF = E
               GOTO 21
            END IF
 20      CONTINUE
 21      CONTINUE
      END IF
      KMIN = EMAX - MAXEXPONENT(V)
      KMAX = EMIN - (MINEXPONENT(V) - DIGITS(V)) - 1
      K = MIN(MAX(KPREF, KMIN), KMAX)
C     values that lose bits: internally below the normal range and not
C     exactly representable there
      IF (EMIN - K .LT. MINEXPONENT(V)) THEN
         DO 30 I = 1, NPIX
            V = PIX(I)
            IF (V .NE. 0 .AND. FINITED(V)) THEN
               IF (EXPONENT(V) - K .LT. MINEXPONENT(V)) THEN
                  W = SCALE(V, -K)
                  IF (SCALE(W, K) .NE. V) NINEX = NINEX + 1
               END IF
            END IF
 30      CONTINUE
      END IF
      RETURN
      END

C     PIX = PIX * 2**K for every pixel (0, NaN and Inf unchanged).
      SUBROUTINE SCALEIMD(PIX, NPIX, K)
      IMPLICIT NONE
      INTEGER*8 NPIX, I
      INTEGER K
      DOUBLE PRECISION PIX(NPIX)
      IF (K .EQ. 0) RETURN
      DO 10 I = 1, NPIX
         PIX(I) = SCALE(PIX(I), K)
 10   CONTINUE
      RETURN
      END

C     A clean message when memory for the double backend is not there.
      SUBROUTINE NOMEMD(WHAT, BYTES)
      IMPLICIT NONE
      CHARACTER*(*) WHAT
      DOUBLE PRECISION BYTES
      CHARACTER*16 MIBD
      WRITE (0,'(5A)') 'elliprof: error (double precision, '
     $     //'memory): cannot allocate ', WHAT, ' (',
     $     TRIM(MIBD(BYTES)),
     $     ' MiB); use --precision single or a machine with more memory'
      RETURN
      END

C     BYTES in MiB, one decimal, left-adjusted (0.2, not .2).
      CHARACTER*16 FUNCTION MIBD(BYTES)
      IMPLICIT NONE
      DOUBLE PRECISION BYTES
      WRITE (MIBD,'(F16.1)') BYTES/1048576D0
      MIBD = ADJUSTL(MIBD)
      RETURN
      END

C     --nonfinite for the double image: as NONFINS (prep.f).
      SUBROUTINE NONFIND(PIX, NCOL, NROW, MASK, GOOD, NNF)
      IMPLICIT NONE
      INTEGER NCOL, NROW, NNF, I, J
      DOUBLE PRECISION PIX(NCOL,NROW)
      LOGICAL MASK, GOOD(NCOL,NROW), FINITED
      NNF = 0
      DO 10 J = 1, NROW
         DO 11 I = 1, NCOL
            IF (.NOT. FINITED(PIX(I,J))) THEN
               NNF = NNF + 1
               IF (MASK) THEN
                  PIX(I,J) = 0
                  GOOD(I,J) = .FALSE.
               END IF
            END IF
 11      CONTINUE
 10   CONTINUE
      RETURN
      END

C     The NaN/Inf count of NONFIND, without masking (keep, error).
      SUBROUTINE NONFCNTD(PIX, NCOL, NROW, NNF)
      IMPLICIT NONE
      INTEGER NCOL, NROW, NNF, I, J
      DOUBLE PRECISION PIX(NCOL,NROW)
      LOGICAL FINITED
      NNF = 0
      DO 10 J = 1, NROW
         DO 11 I = 1, NCOL
            IF (.NOT. FINITED(PIX(I,J))) NNF = NNF + 1
 11      CONTINUE
 10   CONTINUE
      RETURN
      END
