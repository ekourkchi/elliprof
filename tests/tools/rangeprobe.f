C     Range-protection probe (tests/unit/test_range_guards.py): calls
C     the double backend's own GETCONTOURD (bilinear sample, R4),
C     ALTERD (log-fit I0 update, R5), EXPSC2D (R6) and SLOPED (the
C     isophote slope, R7), linked from the same objects as
C     elliprof_native.  One case per input line, every
C     value a binary64 bit pattern (Z16); one result per output line:
C       B x y p00 p10 p01 p11 f0  -> contour at (x,y) (radius 0)
C       A f0 gain c1 c4           -> I0 after one log-fit update
C       E arg k                   -> exp(arg)*2**k  (k as a double)
C       S a1 a2 a0 r0 r1 r2       -> (a1-a2)/a0 * r0/(r1-r2)
      PROGRAM RANGEPROBE
      IMPLICIT DOUBLE PRECISION (A-H,O-Z)
      DOUBLE PRECISION EXPSC2D, SLOPED
      CHARACTER*1 T
      INTEGER*8 IV(7)
      DOUBLE PRECISION V(7), R, PAR(11), FC(9), DATA(12,12), C(1)
      EQUIVALENCE (IV, V)
 1    READ (5,'(A1,1X,7Z17)',END=9) T, IV
      IF (T .EQ. 'B') THEN
         DO 3 J = 1, 12
            DO 2 I = 1, 12
               DATA(I,J) = 1
 2          CONTINUE
 3       CONTINUE
         IX = NINT(V(1))
         IY = NINT(V(2))
         DATA(IX,IY) = V(3)
         DATA(IX+1,IY) = V(4)
         DATA(IX,IY+1) = V(5)
         DATA(IX+1,IY+1) = V(6)
         PAR(1) = 0
         PAR(2) = V(1)
         PAR(3) = V(2)
         PAR(4) = V(7)
         PAR(5) = 90
         PAR(6) = 1
         CALL GETCONTOURD(PAR, 0, 1, C, 12, 12, DATA, 0)
         R = C(1)
      ELSE IF (T .EQ. 'A') THEN
         DO 4 I = 1, 9
            FC(I) = 0
 4       CONTINUE
         PAR(1) = 10
         PAR(2) = 50
         PAR(3) = 50
         PAR(4) = V(1)
         PAR(5) = 90
         PAR(6) = 0.7D0
         PAR(11) = -2
         FC(1) = V(3)
         FC(4) = V(4)
         CALL ALTERD(PAR, 1, 1, 0.3D0, FC, V(2))
         R = PAR(4)
      ELSE IF (T .EQ. 'S') THEN
         R = SLOPED(V(1), V(2), V(3), V(4), V(5), V(6))
      ELSE
         R = EXPSC2D(V(1), NINT(V(2)))
      END IF
      WRITE (6,'(Z16.16)') TRANSFER(R, IV(1))
      GOTO 1
 9    END
