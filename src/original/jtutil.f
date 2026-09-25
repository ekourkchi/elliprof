* Various random utilities from JT
      function amedian(n,x)
      real x(2)
      if(n.eq.0) then
         amedian = 0
         return
      else if(n.eq.1) then
         amedian = x(1)
         return
      end if
      do 913 k = 2,n
         amedian = x(k)
         do 914 l = k-1,1,-1
            if(x(l).le.amedian) goto 915
            x(l+1) = x(l)
 914     continue
         l = 0
 915     x(l+1) = amedian
 913  continue
      amedian = 0.5*(x((n+1)/2)+x((n+2)/2))
      return
      end

      SUBROUTINE FITWLPOLY(NPT,X,Y,W,SCALE,NCOEFF,COEFF)
* X and Y are data arrays with NPT points to fit.
* W is a weight array, so that Sum W * (Y-Yfit)**2 is minimized
* SCALE returns A and B,
* where Z = A * (X - B) is the variable given to the polynomials.
* A polynomial of degree NCOEFF-1 is fit and the coefficients are
* returned in COEFF.
      REAL*4 X(NPT), Y(NPT), SCALE(2), W(NPT)
      real*8 coeff(ncoeff)
      call DOFITLPOLY(NPT,X,Y,W,SCALE,NCOEFF,COEFF,1)
      return
      end

      SUBROUTINE FITLPOLY(NPT,X,Y,SCALE,NCOEFF,COEFF)
* X and Y are data arrays with NPT points to fit.
* SCALE returns A and B,
* where Z = A * (X - B) is the variable given to the polynomials.
* A polynomial of degree NCOEFF-1 is fit and the coefficients are
* returned in COEFF.
      REAL*4 X(NPT), Y(NPT), SCALE(2), DUMMY(2)
      real*8 coeff(ncoeff)
      call DOFITLPOLY(NPT,X,Y,DUMMY,SCALE,NCOEFF,COEFF,0)
      return
      end

      SUBROUTINE DOFITLPOLY(NPT,X,Y,W,SCALE,NCOEFF,COEFF,iwgt)
* X and Y are data arrays with NPT points to fit.
* W is a weight array, so that Sum W * (Y-Yfit)**2 is minimized
* SCALE returns A and B,
* where Z = A * (X - B) is the variable given to the polynomials.
* A polynomial of degree NCOEFF-1 is fit and the coefficients are
* returned in COEFF.
      PARAMETER (MAXFIT=8)
      REAL*8 COV(MAXFIT*MAXFIT), VEC(MAXFIT)
      REAL*8 COEFF(NCOEFF)
      REAL*8 A, B, Z, LPI, DET
      REAL*4 X(NPT), Y(NPT), SCALE(2), W(NPT)
      
      scale(1) = x(1)
      scale(2) = x(1)
      do 2 i = 2,npt
         scale(1) = amin1(scale(1),x(i))
         scale(2) = amax1(scale(2),x(i))
 2    continue

      A = 2.0D0 / (SCALE(2) - SCALE(1))
      B = 0.5D0 * (SCALE(2) + SCALE(1))
      
      DO 5 J = 1,NCOEFF
         VEC(J) = 0
 5    CONTINUE
      DO 6 I = 1,NCOEFF*NCOEFF
         COV(I) = 0
 6    CONTINUE
      DO 10 N = 1,NPT
         Z = A * (DBLE(X(N)) - B)
         
         DO 21 J = 1,NCOEFF
            COEFF(J) = LPI(J,Z)
            if(iwgt.eq.0) then
               VEC(J) = VEC(J) + COEFF(J) * Y(N)
            else
               VEC(J) = VEC(J) + COEFF(J) * Y(N) * W(N)
            end if
            DO 20 I = 1,J
               if(iwgt.eq.0) then
                  COV((J-1)*NCOEFF+I) = COV((J-1)*NCOEFF+I) + 
     $                 COEFF(I) * COEFF(J)
               else
                  COV((J-1)*NCOEFF+I) = COV((J-1)*NCOEFF+I) + 
     $                 COEFF(I) * COEFF(J) * W(N)
               end if
 20         CONTINUE
 21      CONTINUE
 10   CONTINUE
      
      DO 31 J = 2,NCOEFF
         DO 30 I = 1,J-1
            COV((I-1)*NCOEFF+J) = COV((J-1)*NCOEFF+I)
 30      CONTINUE
 31   CONTINUE
      CALL INVERT(NCOEFF,COV,DET)
      IF(DET.EQ.0) THEN
         WRITE(6,*) 'FITWLPOLY: singular covariance matrix'
         RETURN
      END IF
      
      DO 41 J = 1,NCOEFF
         COEFF(J) = 0
         DO 40 I = 1,NCOEFF
            COEFF(J) = COEFF(J) + COV((J-1)*NCOEFF+I) * VEC(I)
 40      CONTINUE
 41   CONTINUE
      SCALE(1) = sngl(A)
      SCALE(2) = sngl(B)
      
      RETURN
      END
      
      SUBROUTINE FIT2DLPOLY(NPT,X,Y,Z,SCALE,NCX,NCY,COEFF)
* X, Y and Z are data arrays with NPT points to fit.
* SCALE receives XMIN, XMAX, YMIN and YMAX and returns AX, BX, AY, BY
* where X' = AX * (X - BX)  and Y' = AY * (Y - BY)
* A two-dimensional polynomial of degree NCX-1 in X and NCY-1 in Y
* is fit and the coefficients are returned in COEFF.
      PARAMETER (MAXFIT=8)
      REAL*8 COV(MAXFIT*MAXFIT*MAXFIT*MAXFIT), VEC(MAXFIT*MAXFIT)
      REAL*8 COEFF(NCX*NCY)
      REAL*8 AX, BX, AY, BY, XSC, YSC, LPI, DET
      REAL*4 X(1), Y(1), Z(1), SCALE(4)

      AX = 2.0D0 / (SCALE(2) - SCALE(1))
      BX = 0.5D0 * (SCALE(2) + SCALE(1))
      AY = 2.0D0 / (SCALE(4) - SCALE(3))
      BY = 0.5D0 * (SCALE(4) + SCALE(3))

      NFIT = NCX*NCY

      DO 5 J = 1,NFIT
       VEC(J) = 0
 5    continue
      DO 6 I = 1,NFIT*NFIT
       COV(I) = 0
 6     continue
      DO 10 N = 1,NPT
      XSC = AX * (X(N) - BX)
      YSC = AY * (Y(N) - BY)

      DO 20 J = 1,NFIT
      JX = (J-1)/NCY + 1
      JY = MOD(J-1,NCY) + 1
      COEFF(J) = LPI(JX,XSC) * LPI(JY,YSC)
      VEC(J) = VEC(J) + COEFF(J) * Z(N)
      DO I = 1,J
         COV(I+(J-1)*NFIT) = COV(I+(J-1)*NFIT) + COEFF(I) * COEFF(J)
      end do
 20   continue
10    CONTINUE

      DO J = 2,NFIT
         DO I = 1,J-1
            COV(J+(I-1)*NFIT) = COV(I+(J-1)*NFIT)
         end do
      end do
      CALL INVERT(NFIT,COV,DET)
      IF(DET.EQ.0) THEN
          WRITE(6,*) 'FIT2DLPOLY: singular covariance matrix'
          RETURN
      END IF

      DO J = 1,NFIT
         COEFF(J) = 0
         DO I = 1,NFIT
            COEFF(J) = COEFF(J) + COV(I+(J-1)*NFIT) * VEC(I)
         end do
      end do
      SCALE(1) = sngl(AX)
      SCALE(2) = sngl(BX)
      SCALE(3) = sngl(AY)
      SCALE(4) = sngl(BY)

      RETURN
      END

      REAL FUNCTION LPOLY2D(X,Y,SCALE,NCX,NCY,COEFF)
* The desired fit has NCX coefficients in X and NCY in Y.
      REAL*8 COEFF(NCX*NCY), XSC, YSC, LPI, TEMP
      REAL*4 SCALE(4)

      NFIT = NCX*NCY

      XSC = SCALE(1) * (X - SCALE(2))
      YSC = SCALE(3) * (Y - SCALE(4))

      TEMP = 0

      DO J = 1,NFIT
         JX = (J-1)/NCY + 1
         JY = MOD(J-1,NCY) + 1
         TEMP = TEMP + COEFF(J) * LPI(JX,XSC) * LPI(JY,YSC)
      end do

      LPOLY2D = sngl(TEMP)

      RETURN
      END

      REAL FUNCTION POLY2D(X,Y,NCX,NCY,COEFF)
* The desired fit has NCX coefficients in X and NCY in Y.
      REAL*8 COEFF(NCX*NCY), T1, T2, DX, DY

      DX = DBLE(X)
      DY = DBLE(Y)

      T2 = 0

      DO 900 J = NCX*NCY,NCY,-NCY
          T1 = 0
          DO 901 I = J,J-NCY+1,-1
              T1 = T1 * DY + COEFF(I)
901       CONTINUE
          T2 = T2 * DX + T1
900   CONTINUE

      POLY2D = sngl(T2)

      RETURN
      END

      REAL FUNCTION LPOLY(X,SCALE,NCOEFF,COEFF)
      REAL*8 COEFF(1)
      REAL*8 TEMP, Z, LPI
      REAL*4 SCALE(2)
      Z = SCALE(1) * (X - SCALE(2))
      TEMP = 0
      DO 10 I = 1,NCOEFF
         TEMP = TEMP + COEFF(I) * LPI(I,Z)
 10   CONTINUE
      LPOLY = sngl(TEMP)
      RETURN
      END

      FUNCTION LPI(I,Z)
* Legendre polynomial of order i-1
      REAL*8 LPI, Z, LP0, LP1, LP2, LP3, LP4, LP5, LP6, LP7
      LP0(Z)=1D0
      LP1(Z)=Z
      LP2(Z)=    -.5D0+1.5D0*Z*Z
      LP3(Z)=Z*(-1.5D0+2.5D0*Z*Z)
      LP4(Z)=    .375D0+Z*Z*(-3.75D0+4.375D0*Z*Z)
      LP5(Z)=Z*(1.875D0+Z*Z*(-8.75D0+7.875*Z*Z))
      LP6(Z)=   -.3125D0+Z*Z*(6.5625D0+Z*Z*(-19.6875D0+14.4375D0*Z*Z))
      LP7(Z)=Z*(-2.1875D0+Z*Z*(19.6875D0+Z*Z*(-43.3125D0+26.8125D0*Z*Z))
     $     )

      GOTO(1,2,3,4,5,6,7,8) I
1     LPI = LP0(Z)
      RETURN
2     LPI = LP1(Z)
      RETURN
3     LPI = LP2(Z)
      RETURN
4     LPI = LP3(Z)
      RETURN
5     LPI = LP4(Z)
      RETURN
6     LPI = LP5(Z)
      RETURN
7     LPI = LP6(Z)
      RETURN
8     LPI = LP7(Z)
      RETURN
      END

      SUBROUTINE INVERT(N,A,DET)
C     INVERT's arguments:
C
C     N - The dimension of the matrix
C     A - The NxN matrix to be inverted. Upon successful inversion, A
C         contains the inverse. A must be real*8
C     RST - A Nx1 scratch vector (the row status vector)
C     DET - The determinant of the matrix. DET is set to 0 for a
C         singular matrix, and in that case, A contains garbage.
C
      PARAMETER (MAXN=2048)
      REAL*8 A(N,N), SAVE, PIVOT, ONROW, CPREV, CNOW, DET, DECR
      INTEGER*2 RST(2,MAXN)
C
      if(n .gt. MAXN) then
         write(6,*) 'INVERT: not enough storage for RST'
         det = 0.0
         return
      end if
      MRANK = 0
      ISIGN = 1
      DET = 0.
      DO J = 1,N
         DO I = 1,2
            RST(I,J) = 0
         end do
      end do
C
C     Loop over columns, reducing each
C
      DO 500 I = 1,N
C
C     Find the pivot element
C
      PIVOT = 0
      NROW = 0
      NCOL = 0
      DO 30 J = 1,N
         IF(RST(1,J).NE.0) GO TO 30
         DO 20 K = 1,N
            IF(RST(1,K).NE.0) GO TO 20
            IF(PIVOT.GE.DABS(A(J,K))) GO TO 20
            PIVOT = DABS(A(J,K))
            NROW = J
            NCOL = K
 20      CONTINUE
30    CONTINUE
      PIVOT = A(NROW,NCOL)
      IF(PIVOT.EQ.0) GO TO 300
      RST(1,NCOL) = int(NROW, 2)
      RST(2,NCOL) = int(I, 2)
C
C     Swap pivot element onto the diagonal
C
      DO K = 1,N
         SAVE = A(NROW,K)
         A(NROW,K) = A(NCOL,K)
         A(NCOL,K) = SAVE
      end do
C
C     Reduce pivot column
C
      DO J = 1,N
         A(J,NCOL) = -A(J,NCOL)/PIVOT
      end do
      A(NCOL,NCOL) = 1/PIVOT
C
C     Reduce other columns
C
      DO 60 K = 1,N
      IF(K.EQ.NCOL) GO TO 60
C
C     Find maximum of column to check for singularity
C
      CPREV = 0
      DO J = 1,N
         CPREV = DMAX1(CPREV,DABS(A(J,K)))
      end do
C
C     Reduce the column
C
      ONROW = A(NCOL,K)
      A(NCOL,K) = 0
      DO J = 1,N
         A(J,K) = A(J,K) + ONROW*A(J,NCOL)
      end do
C
C     Find the new maximum of the column
C
      CNOW = 0
      DO J = 1,N
         CNOW = DMAX1(CNOW,DABS(A(J,K)))
      end do
C
C     Quit if too many figures accuracy were lost (singular)
C
      IF(CNOW.EQ.0) GOTO 300
      DECR = CPREV / CNOW
      IF(DECR.GT.1D8) GO TO 300
C
60    CONTINUE
C
      DET = DET + DLOG10(DABS(PIVOT))
      IF(PIVOT.LT.0) ISIGN = -ISIGN
      MRANK = MRANK + 1
500   continue
C
C     Now untangle the mess
C
      DO 100 J = 1,N
      DO 110 K = 1,N
      IF(RST(2,K).NE.(N + 1 - J)) GO TO 110
      NCOL = RST(1,K)
      IF(NCOL.EQ.K) GO TO 100
      DO L = 1,N
         SAVE = A(L,NCOL)
         A(L,NCOL) = A(L,K)
         A(L,K) = SAVE
      end do
      GO TO 100
110   CONTINUE
100   CONTINUE
      IF(ABS(DET).LT.35) DET = ISIGN*10.**DET
      RETURN
C
C     Singular exit
C
300   DET = 0
      RETURN
C
      END

      SUBROUTINE POLYC(NC,SCALE,COEFF,PCOEFF)
* Routine to convert coefficients of a 1-d Legendre polynomial to
* coefficients of a plain polynomial
* The NC coefficients are stored with the low order coefficient first
      REAL*8 COEFF(1), PCOEFF(1), SC(2), TEMP
      REAL*4 SCALE(2)
      REAL*8 LCOEFF(8,8)
      DATA LCOEFF /
     1    1D0,0D0,0D0,0D0,0D0,0D0,0D0,0D0,
     1    0D0,1D0,0D0,0D0,0D0,0D0,0D0,0D0,
     1    -.5D0,0D0,1.5D0,0D0,0D0,0D0,0D0,0D0,
     1    0D0,-1.5D0,0D0,2.5D0,0D0,0D0,0D0,0D0,
     1    .375D0,0D0,-3.75D0,0D0,4.375D0,0D0,0D0,0D0,
     1    0D0,1.875D0,0D0,-8.75D0,0D0,7.875,0D0,0D0,
     1    -.3125D0,0D0,6.5625D0,0D0,-19.6875D0,0D0,14.4375D0,0D0,
     1    0D0,-2.1875D0,0D0,19.6875D0,0D0,-43.3125D0,0D0,26.8125D0/

      SC(1) = DBLE(SCALE(1))
      SC(2) = DBLE(SCALE(2))
      DO 900 K = 0,NC-1
          TEMP = 0
          DO 901 I = K,NC-1
              TEMP = TEMP + COEFF(I+1) * LCOEFF(K+1,I+1)
901       CONTINUE
          PCOEFF(K+1) = TEMP
900   CONTINUE
      DO 902 K = 0,NC-1
         IF(SC(2).NE.0) THEN
            TEMP = 0
            DO 903 I = K,NC-1
               TEMP = TEMP + PCOEFF(I+1) * SC(1)**I *
     1              (-SC(2))**(I-K) * DFLOAT(IBC(K,I))
 903        CONTINUE
            PCOEFF(K+1) = TEMP
         ELSE
            PCOEFF(K+1) = PCOEFF(K+1) * SC(1)**K
         END IF
902   CONTINUE

      RETURN
      END

      SUBROUTINE POLYCC(NX,NY,SCALE,COEFF,PCOEFF)
* Routine to convert coefficients of a 2-d Legendre polynomial to
* coefficients of a plain polynomial
* The coefficients are stored as NX polynomials of order NY-1.
* Low order coefficient comes first, and the low order coefficient
* of the x polynomial is obtained by evaluating the first y polynomial.
      REAL*8 COEFF(1), PCOEFF(1), XSC(2), YSC(2), TEMP
      REAL*4 SCALE(4)
      REAL*8 LCOEFF(8,8)
      DATA LCOEFF /
     1    1D0,0D0,0D0,0D0,0D0,0D0,0D0,0D0,
     1    0D0,1D0,0D0,0D0,0D0,0D0,0D0,0D0,
     1    -.5D0,0D0,1.5D0,0D0,0D0,0D0,0D0,0D0,
     1    0D0,-1.5D0,0D0,2.5D0,0D0,0D0,0D0,0D0,
     1    .375D0,0D0,-3.75D0,0D0,4.375D0,0D0,0D0,0D0,
     1    0D0,1.875D0,0D0,-8.75D0,0D0,7.875,0D0,0D0,
     1    -.3125D0,0D0,6.5625D0,0D0,-19.6875D0,0D0,14.4375D0,0D0,
     1    0D0,-2.1875D0,0D0,19.6875D0,0D0,-43.3125D0,0D0,26.8125D0/

      XSC(1) = DBLE(SCALE(1))
      XSC(2) = DBLE(SCALE(2))
      YSC(1) = DBLE(SCALE(3))
      YSC(2) = DBLE(SCALE(4))

      DO 10 J = 0,NX-1
      DO 11 K = 0,NY-1
          TEMP = 0
          DO 12 I = K,NY-1
              TEMP = TEMP + COEFF(J*NY+I+1) * LCOEFF(K+1,I+1)
12        CONTINUE
          PCOEFF(J*NY+K+1) = TEMP
11    CONTINUE
      DO 13 K = 0,NY-1
* (010904 JT) fixed up mess
         IF(YSC(2).NE.0) THEN
            TEMP = 0
            DO 900 I = K,NY-1
               TEMP = TEMP + PCOEFF(J*NY+I+1) * YSC(1)**I *
     1              (-YSC(2))**(I-K) * DFLOAT(IBC(K,I))
 900        CONTINUE
            PCOEFF(J*NY+K+1) = TEMP
         ELSE
            PCOEFF(J*NY+K+1) = PCOEFF(J*NY+K+1) * YSC(1)**K
         END IF
13    CONTINUE
10    CONTINUE

      DO 20 J = 0,NY-1
      DO 21 K = 0,NX-1
          TEMP = 0
          DO 22 I = K,NX-1
              TEMP = TEMP + PCOEFF(I*NY+J+1) * LCOEFF(K+1,I+1)
22        CONTINUE
          PCOEFF(K*NY+J+1) = TEMP
21    CONTINUE
      DO 23 K = 0,NX-1
         IF(XSC(2).NE.0) THEN
            TEMP = 0
            DO 901 I = K,NX-1
               TEMP = TEMP + PCOEFF(I*NY+J+1) * XSC(1)**I *
     1              (-XSC(2))**(I-K) * DFLOAT(IBC(K,I))
 901        CONTINUE
            PCOEFF(K*NY+J+1) = TEMP
         ELSE
            PCOEFF(K*NY+J+1) = PCOEFF(K*NY+J+1) * XSC(1)**K
         END IF
23    CONTINUE
20    CONTINUE

      RETURN
      END

      FUNCTION IBC(M,N)
* Returns the (m n) binomial coefficient
      IBC = 1
      DO 900 I = M+1,N
          IBC = IBC * I
900   CONTINUE
      DO 901 I = 2,N-M
          IBC = IBC / I
901   CONTINUE
      RETURN
      END

      function bc(n,k)
* Binomial coefficient of (n k), divided by 2^n
      inum = 1
      idenom = 1
      do 10 i = k+1,n
         inum = inum * i
         idenom = idenom * (i-k)
 10   continue
      ibc = inum / idenom
      bc = float(ibc)/2**n
      return
      end

      FUNCTION ZBRENT(FUNC,X1,X2,fx1,fx2,TOL)
      PARAMETER (ITMAX=100,EPS=3.E-8)
      EXTERNAL FUNC
      zbrent = 0
      A=X1
      B=X2
C      FA=FUNC(A)
C      FB=FUNC(B)
      FA=Fx1
      FB=Fx2
      IF(FB*FA.GT.0.) THEN
         write(6,*) 'Root must be bracketed for ZBRENT.'
         return
      END IF
      FC=FB
      DO 11 ITER=1,ITMAX
        IF(FB*FC.GT.0.) THEN
          C=A
          FC=FA
          D=B-A
          E=D
        ENDIF
        IF(ABS(FC).LT.ABS(FB)) THEN
          A=B
          B=C
          C=A
          FA=FB
          FB=FC
          FC=FA
        ENDIF
        TOL1=2.*EPS*ABS(B)+0.5*TOL
        XM=.5*(C-B)
        IF(ABS(XM).LE.TOL1 .OR. FB.EQ.0.)THEN
          ZBRENT=B
          RETURN
        ENDIF
        IF(ABS(E).GE.TOL1 .AND. ABS(FA).GT.ABS(FB)) THEN
          S=FB/FA
          IF(A.EQ.C) THEN
            P=2.*XM*S
            Q=1.-S
          ELSE
            Q=FA/FC
            R=FB/FC
            P=S*(2.*XM*Q*(Q-R)-(B-A)*(R-1.))
            Q=(Q-1.)*(R-1.)*(S-1.)
          ENDIF
          IF(P.GT.0.) Q=-Q
          P=ABS(P)
          IF(2.*P .LT. MIN(3.*XM*Q-ABS(TOL1*Q),ABS(E*Q))) THEN
            E=D
            D=P/Q
          ELSE
            D=XM
            E=D
          ENDIF
        ELSE
          D=XM
          E=D
        ENDIF
        A=B
        FA=FB
        IF(ABS(D) .GT. TOL1) THEN
          B=B+D
        ELSE
          B=B+SIGN(TOL1,XM)
        ENDIF
        FB=FUNC(B)
11    CONTINUE
      write(6,*) 'ZBRENT exceeding maximum iterations.'
      ZBRENT=B
      RETURN
      END

