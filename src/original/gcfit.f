      subroutine arraycenter(nx,ny,xcent,ycent,xwidth,ywidth,data)
      parameter (maxpixdim=2048)
      real data(nx,ny)
      real line(maxpixdim)
      real cent, cent2, sum

      cent = 0.0
      cent2 = 0.0
      sum = 0.0
      do 10 i = 1,nx
         line(i) = 0.0
         do 11 j = 1,ny
           line(i) = line(i) + data(i,j)
 11      continue
         cent = cent + i * line(i)
         cent2 = cent2 + i * i * line(i)
         sum = sum + line(i)
 10   continue
      xcent = cent / sum
      xwidth = cent2 / sum - xcent * xcent
      if (xwidth.gt.0) then
         xwidth = sqrt(xwidth)
      else
         xwidth = 0.0
      end if

      cent = 0.0
      cent2 = 0.0
      sum = 0.0
      do 12 i = 1,ny
         line(i) = 0.0
         do 13 j = 1,nx
           line(i) = line(i) + data(j,i)
 13      continue
         cent = cent + i * line(i)
         cent2 = cent2 + i * i * line(i)
         sum = sum + line(i)
 12   continue
      ycent = cent / sum
      ywidth = cent2 / sum - ycent * ycent
      if (ywidth.gt.0) then
         ywidth = sqrt(ywidth)
      else
         ywidth = 0.0
      end if

      return
      end

      subroutine makegcmodel(nx,ny,data,param,nradtot,nrad,xcent,
     $     ycent, width)
      parameter (maxrad=250,alp=7.669,maxfit=20)
      real data(nx,ny), param(11,maxrad)
      real*4 x(maxrad), y(maxrad), ysig(maxrad)
      real*4 a(maxfit), covar(maxfit,maxfit), alpha(maxfit,maxfit)
      real*4 b
      integer lista(maxfit)
      external funcs

* Keep compiler happy
      if(nrad.eq.0) i=0

C First, get average radius of each annulus. Use ravg=(r2-r1)*(4/5)^4,
C which is ravg=0.4096*(r2-r1)
      do 10 k=nradtot,2,-1
         param(1,k) = 0.4096 * (param(1,k) - param(1,k-1))
     $        + param(1,k-1)
 10   continue
C Treat first annulus separately:
      param(1,1) = 0.4096 * param(1,1)

C 
C Then, initialize the arrays.
      do 11 k=1,nradtot
         x(k) = param(1,k)
         if(param(4,k).gt.0.0) then
            y(k) = param(4,k)
            ysig(k) = param(5,k)
         else
            nradtot = k - 1
            goto 14
         end if
 11   continue

C If last annulus has less than 20% of pixels of next-to-last, omit it.
 14   if(param(6,nradtot)/param(6,nradtot-1).lt.0.20) then
         nradtot = nradtot - 1
      endif

      write(6,*) 'These are for the fit . . .'
      write(6,*) '  n   r          I      rms'
      do 15 k=1,nradtot
         write(6,1100) k, x(k), y(k), ysig(k)
 1100    format(i4,f9.4,f9.4,f9.4)
 15   continue
         
      ma = 4
      mfit = 4
      lista(1) = 1
      lista(2) = 2
      lista(3) = 3
      lista(4) = 4
      a(1) = param(4,1)
      a(2) = -0.04 * param(4,1)
      a(3) =  0.02 * param(4,1)
      a(4) = width/2.0
      alamda = -1.0
      alamold = 100.0
      chiold = 1.0e10
      write(6,*) '   lamda      chisq    a(1) . . .' 
 18   call mrqmin(x,y,ysig,nradtot,a,ma,lista,mfit,covar,alpha,
     $     ma,chisq,funcs,alamda)
      if ((alamda.gt.alamold.or.(chisq/chiold).lt.0.999
     $     .or.chisq.gt.chiold).and.alamda.lt.1e10) then
         alamold = alamda
         chiold = chisq
         write(6,1801) alamda, chisq, a(1), a(2), a(3), a(4)
         goto 18
      end if
 1801 format(6(1pe10.3,1x))

      write (6,*) 'chisq = ', chisq
      write (6,*) 'I(0) =', a(1)
      write (6,*) 'rc =', a(4)
      write (6,*) 'rt =', a(4)*sqrt(4*a(1)*a(1)/(a(2)*a(2)) - 1.)
      write (6,*) 'sky =', a(3) + 0.5*a(2)
      write (6,*) '   rad      I       Ifit'
      do 19 k=1,nradtot
         r = param(1,k)
         b = 1.0 / (1.0 + (r*r)/(a(4)*a(4)))
         fiti =  a(1)*b + a(2)*sqrt(b) + a(3)
         write(6,1101) r, param(4,k), fiti
 19   continue
 1101    format(f8.2,f9.1,f9.1)

      do 12 i=1,nx
         do 13 j=1,ny
            r = sqrt((i-xcent)*(i-xcent)+(j-ycent)*(j-ycent))
            b = 1.0 / (1.0 + (r*r)/(a(4)*a(4)))
            data(i,j) =  a(1)*b + a(2)*sqrt(b) + a(3)
 13      continue
 12   continue
     
      return
      end


      subroutine funcs(x,a,yfit,dyda,ma)
      parameter (alp=7.669)
      real*4 a(ma), dyda(ma), b

C This is a King model....
C      yfit = a(3) * ( 1.0/sqrt(1.0 + x*x/(a(1)*a(1))) -
C     $     1.0/sqrt(1.0 + a(2)*a(2)/(a(1)*a(1))) )**2 + a(4)
C      dyda(1) = 2.0*a(3) * ( x*x/a(1)**3 * (1.0 +
C     $     x*x/(a(1)*a(1)))**(-1.5) - a(2)*a(2)/a(1)**3 *
C     $     (1.0 + a(2)*a(2)/(a(1)*a(1)))**(-1.5))
C      dyda(2) = a(3)*a(2)/(a(1)*a(1)) * (1.0 +
C     $     a(2)*a(2)/(a(1)*a(1)))**(-1.5)
C      dyda(3) = ( 1.0/sqrt(1.0 + x*x/(a(1)*a(1))) -
C     $     1.0/sqrt(1.0 + a(2)*a(2)/(a(1)*a(1))) )**2
C      dyda(4) = 1.0

C This way is much more stable....

      b = 1.0 / (1.0 + (x*x)/(a(4)*a(4)))
      yfit = a(1)*b + a(2)*sqrt(b) + a(3)
      dyda(1) = b
      dyda(2) = sqrt(b)
      dyda(3) = 1.0
      dyda(4) = (2.0*x*x*b*b*a(1) + x*x*sqrt(b*b*b)*a(2)) /
     $     (a(4)*a(4)*a(4))
      return
      end


      subroutine lsfit(x,y,ndata,sig,mwt,a,b,siga,sigb,chi2,q)
C Given a set of ndata points x(i),y(i) with standard deviations of sig(i)
C in y(i), fit them to a line y = a + bx by minimizing chi^2.  Returned are
C a,b and their respective probable uncertainties siga and sigb, the
C chi-square chi2, and the goodness-of-fit probability q (that the fit would
C have chi2 this large or larger).  If mwt=0 on input, then the standard
C standard deviations are assumed to be unavailable:  q is returned as 1.0
C and the normalization of chi2 is to unit standard deviation on all points.

      real*4 x(ndata), y(ndata), sig(ndata)
      sx=0.0
      sy=0.0
      st2=0.0
      b=0.0
      if (mwt.ne.0) then
         ss=0.0
         do 11 i=1,ndata
            wt = 1.0 / (sig(i)**2)
            ss = ss + wt
            sx = sx + x(i)*wt
            sy = sy + y(i)*wt
 11      continue
      else
         do 12 i=1,ndata
            sx = sx + x(i)
            sy = sy + y(i)
 12      continue
         ss = float(ndata)
      end if

      sxoss = sx/ss
      if (mwt.ne.0) then
         do 13 i=1,ndata
            t = (x(i) - sxoss) / sig(i)
            st2 = st2 + t*t
            b = b + t * y(i)/sig(i)
 13      continue
      else
         do 14 i=1,ndata
            t = x(i) - sxoss
            st2 = st2 + t*t
            b = b + t*y(i)
 14      continue
      end if

      b = b / st2
      a = (sy - sx*b) / ss
      siga = sqrt((1.0 + sx*sx / (ss*st2)) / ss)
      sigb = sqrt(1.0 / st2)
      chi2 = 0.0
      if (mwt.eq.0) then
         do 15 i=1,ndata
            chi2 = chi2 + (y(i) - a - b*x(i))**2
 15      continue
         q = 1.0
         sigdat = sqrt(chi2/(ndata - 2))
         siga = siga*sigdat
         sigb = sigb*sigdat
      else
         do 16 i=1,ndata
            chi2 = chi2 + ((y(i) - a - b*x(i)) / sig(i))**2
 16      continue
         q = gammq(0.5 * (ndata - 2), 0.5 * chi2)
      end if
      return
      end

      function gammq(a,x)
C Returns the incomplete gamma function Q(a,x) = 1 - P(a,x)
      if (x.lt.0.0.or.a.le.0.0) write(6,*) 'gammq: bad arg(s)'
      if (x.lt.a+1.0) then
         call gser(gamser,a,x,gln)
         gammq = 1.0 - gamser
      else
         call gcf(gammcf,a,x,gln)
         gammq = gammcf
      end if
      return
      end


      subroutine gser(gamser,a,x,gln)
C Returns the incomplete gamma function P(a,x) evaluated by its series
C representation as gamser.  Also return ln(gamma(a)) as gln.
      parameter (itmax=100, eps=3.0e-7)
      gln = gammln(a)
      if (x.le.0.0) then
         if (x.lt.0.0) write(6,*) 'gser: x < 0'
         gamser = 0.0
         return
      end if
      ap = a
      sum = 1.0/a
      del = sum
      do 11 n=1,itmax
         ap = ap + 1.0
         del = del * x / ap
         sum = sum + del
         if(abs(del).lt.abs(sum)*eps) goto 1
 11   continue
      write(6,*) 'gser: a too large, itmax too small'
 1    gamser = sum * exp(-x + a * alog(x) - gln)
      return
      end


      subroutine gcf(gammcf,a,x,gln)
C Returns the incomplete gamma function Q(a,x) evaluated by its continued
C fraction representation as gammcf.  Also returns gamma(a) as gln.
      parameter (itmax=100,eps=3.0e-7)
      gln = gammln(a)
      gold = 0.0
      a0 = 1.0
      a1 = x
      b0 = 0.0
      b1 = 1.0
      fac = 1.0
      do 11 n=1,itmax
         an = float(n)
         ana = an - a
         a0 = (a1 + a0*ana) * fac
         b0 = (b1 + b0*ana) * fac
         anf = an * fac
         a1 = x*a0 + anf*a1
         b1 = x*b0 + anf*b1
         if (a1.ne.0.0) then
            fac = 1.0 / a1
            g = b1*fac
            if (abs((g - gold)/g).lt.eps) goto 1
            gold = g
         end if
 11   continue
      write(6,*) 'gcf: a too large, itmax too small'
 1    gammcf = exp(-x + a*alog(x) - gln) * g
      return
      end


      function gammln(xx)
C Returns the value ln(gamma(xx)) fo xx > 0.  Full accuracy is obtained
C for xx > 1.
      real*8 cof(6),stp,half,one,fpf,x,tmp,ser
      data cof,stp /76.18009173d0,-86.50532033d0,24.01409822d0,
     $     -1.231739516d0,.120858003d-2,-.536382d-5,2.50662827465d0/
      data half,one,fpf /0.5d0,1.0d0,5.5d0/
      x = xx - one
      tmp = x + fpf
      tmp = (x+half) * dlog(tmp) - tmp
      ser = one
      do 11 j=1,6
         x = x + one
         ser = ser + cof(j)/x
 11   continue
      gammln = sngl(tmp + dlog(stp*ser))
      return
      end




      SUBROUTINE MRQMIN(X,Y,SIG,NDATA,A,MA,LISTA,MFIT,
     *    COVAR,ALPHA,NCA,CHISQ,FUNCS,ALAMDA)
C Levenberg-Marquardt method, attempting to reduce the value chi^2 of a fit
C between a set of NDATA points X(I),Y(I) with individual standard deviations
C SIG(I) in Y(I), and a nonlinear function dependent on MA coefficients A.
C The array LISTA numbers the parameters A such that the first MFIT elements
C correspond to values actually being adjusted; the remaining MA-MFIT
C parameters are held fixed at their input value.  The program returns the
C current best-fit values for the MA fit parameters A, and chi^2, CHISQR.
C The arrays COVAR(NCA,NCA), ALPHA(NCA,NCA) with physical dimension NCA are
C used as working space during most iterations.  Supply a subroutine
C FUNCS(X,A,YFIT,DYDA,MA) that evaluates the fitting function YFIT, and its
C derivatives DYDA with respect to the fitting parameters A at X.  On the
C first call provide an initial guess for the parameters A, and set ALAMDA<0
C for initialization (which then sets ALAMDA=.001).  If a step succeeds
C CHISQ becomes smaller and ALAMDA decreases by a factor of 10.  If a step
C fails ALAMDA grows by a factor of 10.  You must call this routine
C repeatedly until convergence is achieved.  Then, make one final call with
C ALAMDA=0, so that COVAR(I,J) returns the covariance matrix, and ALPHA(I,J)
C the curvature matrix.

      PARAMETER (MMAX=20)
      DIMENSION X(NDATA),Y(NDATA),SIG(NDATA),A(MA),LISTA(MFIT),
     *  COVAR(NCA,NCA),ALPHA(NCA,NCA),ATRY(MMAX),BETA(MMAX),DA(MMAX)
      EXTERNAL FUNCS
      IF(ALAMDA.LT.0.)THEN
        KK=MFIT+1
        DO 12 J=1,MA
          IHIT=0
          DO 11 K=1,MFIT
            IF(LISTA(K).EQ.J)IHIT=IHIT+1
11        CONTINUE
          IF (IHIT.EQ.0) THEN
            LISTA(KK)=J
            KK=KK+1
          ELSE IF (IHIT.GT.1) THEN
            WRITE(6,*) 'Improper permutation in LISTA'
          ENDIF
12      CONTINUE
        IF (KK.NE.(MA+1)) WRITE(6,*) 'Improper permutation in LISTA'
        ALAMDA=0.001
        CALL MRQCOF(X,Y,SIG,NDATA,A,MA,LISTA,MFIT,ALPHA,BETA,NCA,
     $       CHISQ,FUNCS)
        OCHISQ=CHISQ
        DO 13 J=1,MA
          ATRY(J)=A(J)
13      CONTINUE
      ENDIF
      DO 15 J=1,MFIT
        DO 14 K=1,MFIT
          COVAR(J,K)=ALPHA(J,K)
14      CONTINUE
        COVAR(J,J)=ALPHA(J,J)*(1.+ALAMDA)
        DA(J)=BETA(J)
15    CONTINUE
      CALL GAUSSJ(COVAR,MFIT,NCA,DA,1,1, ierr)
      IF(ALAMDA.EQ.0.)THEN
        CALL COVSRT(COVAR,NCA,MA,LISTA,MFIT)
        RETURN
      ENDIF
      DO 16 J=1,MFIT
        ATRY(LISTA(J))=ATRY(LISTA(J))+DA(J)
16    CONTINUE
      CALL MRQCOF(X,Y,SIG,NDATA,ATRY,MA,LISTA,MFIT,COVAR,DA,NCA,
     $     CHISQ,FUNCS)
      IF(CHISQ.LT.OCHISQ)THEN
        ALAMDA=0.1*ALAMDA
        OCHISQ=CHISQ
        DO 18 J=1,MFIT
          DO 17 K=1,MFIT
            ALPHA(J,K)=COVAR(J,K)
17        CONTINUE
          BETA(J)=DA(J)
          A(LISTA(J))=ATRY(LISTA(J))
18      CONTINUE
      ELSE
        ALAMDA=10.*ALAMDA
        CHISQ=OCHISQ
      ENDIF
      RETURN
      END


      SUBROUTINE MRQCOF(X,Y,SIG,NDATA,A,MA,LISTA,MFIT,ALPHA,BETA,
     $     NALP,CHISQ,FUNCS)
      PARAMETER (MMAX=20)
      DIMENSION X(NDATA),Y(NDATA),SIG(NDATA),ALPHA(NALP,NALP),BETA(MA),
     $    DYDA(MMAX),LISTA(MFIT), A(MA)
      EXTERNAL FUNCS
      DO 12 J=1,MFIT
        DO 11 K=1,J
          ALPHA(J,K)=0.
11      CONTINUE
        BETA(J)=0.
12    CONTINUE
      CHISQ=0.
      DO 15 I=1,NDATA
        CALL FUNCS(X(I),A,YMOD,DYDA,MA)
        SIG2I=1./(SIG(I)*SIG(I))
        DY=Y(I)-YMOD
        DO 14 J=1,MFIT
          WT=DYDA(LISTA(J))*SIG2I
          DO 13 K=1,J
            ALPHA(J,K)=ALPHA(J,K)+WT*DYDA(LISTA(K))
13        CONTINUE
          BETA(J)=BETA(J)+DY*WT
14      CONTINUE
        CHISQ=CHISQ+DY*DY*SIG2I
15    CONTINUE
      DO 17 J=2,MFIT
        DO 16 K=1,J-1
          ALPHA(K,J)=ALPHA(J,K)
16      CONTINUE
17    CONTINUE
      RETURN
      END


      SUBROUTINE COVSRT(COVAR,NCVM,MA,LISTA,MFIT)
      DIMENSION COVAR(NCVM,NCVM),LISTA(MFIT)
      DO 12 J=1,MA-1
        DO 11 I=J+1,MA
          COVAR(I,J)=0.
11      CONTINUE
12    CONTINUE
      DO 14 I=1,MFIT-1
        DO 13 J=I+1,MFIT
          IF(LISTA(J).GT.LISTA(I)) THEN
            COVAR(LISTA(J),LISTA(I))=COVAR(I,J)
          ELSE
            COVAR(LISTA(I),LISTA(J))=COVAR(I,J)
          ENDIF
13      CONTINUE
14    CONTINUE
      SWAP=COVAR(1,1)
      DO 15 J=1,MA
        COVAR(1,J)=COVAR(J,J)
        COVAR(J,J)=0.
15    CONTINUE
      COVAR(LISTA(1),LISTA(1))=SWAP
      DO 16 J=2,MFIT
        COVAR(LISTA(J),LISTA(J))=COVAR(1,J)
16    CONTINUE
      DO 18 J=2,MA
        DO 17 I=1,J-1
          COVAR(I,J)=COVAR(J,I)
17      CONTINUE
18    CONTINUE
      RETURN
      END


      SUBROUTINE GAUSSJ(A,N,NP,B,M,MP, ierr)
      PARAMETER (NMAX=50)
      DIMENSION A(NP,NP),B(NP,MP),IPIV(NMAX),INDXR(NMAX),INDXC(NMAX)
      DO 11 J=1,N
        IPIV(J)=0
11    CONTINUE
      ierr = 0
      DO 22 I=1,N
        BIG=0.
        DO 13 J=1,N
          IF(IPIV(J).NE.1)THEN
            DO 12 K=1,N
              IF (IPIV(K).EQ.0) THEN
                IF (ABS(A(J,K)).GE.BIG)THEN
                  BIG=ABS(A(J,K))
                  IROW=J
                  ICOL=K
                ENDIF
              ELSE IF (IPIV(K).GT.1) THEN
C                WRITE(6,*) 'Singular matrix'
                ierr = 1
                return
              ENDIF
12          CONTINUE
          ENDIF
13      CONTINUE
        IPIV(ICOL)=IPIV(ICOL)+1
        IF (IROW.NE.ICOL) THEN
          DO 14 L=1,N
            DUM=A(IROW,L)
            A(IROW,L)=A(ICOL,L)
            A(ICOL,L)=DUM
14        CONTINUE
          DO 15 L=1,M
            DUM=B(IROW,L)
            B(IROW,L)=B(ICOL,L)
            B(ICOL,L)=DUM
15        CONTINUE
        ENDIF
        INDXR(I)=IROW
        INDXC(I)=ICOL
        IF (A(ICOL,ICOL).EQ.0.) then
C           WRITE(6,*) 'Singular matrix.'
           ierr = 1
           return
        end if
        PIVINV=1./A(ICOL,ICOL)
        A(ICOL,ICOL)=1.
        DO 16 L=1,N
          A(ICOL,L)=A(ICOL,L)*PIVINV
16      CONTINUE
        DO 17 L=1,M
          B(ICOL,L)=B(ICOL,L)*PIVINV
17      CONTINUE
        DO 21 LL=1,N
          IF(LL.NE.ICOL)THEN
            DUM=A(LL,ICOL)
            A(LL,ICOL)=0.
            DO 18 L=1,N
              A(LL,L)=A(LL,L)-A(ICOL,L)*DUM
18          CONTINUE
            DO 19 L=1,M
              B(LL,L)=B(LL,L)-B(ICOL,L)*DUM
19          CONTINUE
          ENDIF
21      CONTINUE
22    CONTINUE
      DO 24 L=N,1,-1
        IF(INDXR(L).NE.INDXC(L))THEN
          DO 23 K=1,N
            DUM=A(K,INDXR(L))
            A(K,INDXR(L))=A(K,INDXC(L))
            A(K,INDXC(L))=DUM
23        CONTINUE
        ENDIF
24    CONTINUE
      RETURN
      END

