        SUBROUTINE ELLIPROF(DATA,NROW,NCOL)

C Find the isophote profile and parameters of an object in an image.

Chelp*cmd elliprof    - fit isophotes and params of an object in an image
Chelp
Chelp Elliprof is used to find the surface brightness profile of an
Chelp object in an image by describing the object as a set of elliptical
Chelp contours. The profile is found
Chelp by sampling the image grid with a set of ellipses with semi-major
Chelp axes specified by the user. Low order sine
Chelp and cosine transforms are taken along the contour to derive
Chelp its center, position angle, and ellipticity.  After these are found
Chelp for the entire range in radius specified, the contours are adjusted
Chelp to more accurately fit the isophotes.
Chelp
Chelp The results of the profile calculation are stored in a common
Chelp block for future examination or storage by the PLOT, PRINT, SAVE
Chelp and GET commands.  The surface brightness of the profile as a function
Chelp of contour major axis is loaded into a spectrum buffer for ease in
Chelp examination and manipulation.
Chelp
Chelp If desired, the program will replace the data with a synthetic image
Chelp derived from the profile fit.
Chelp
Chelp Syntax: elliprof buffer [options]
Chelp
Chelp Options:
Chelp    X0=x            x position of the center
Chelp    Y0=y            y position of the center
Chelp    R0=r0           Inner radius to fit
Chelp    R1=r1           Outer radius to fit
Chelp    NR=n            Number of radii to fit
Chelp    RLAW=k          0/1/2 for linear/log/r^0.25 r steps
Chelp    LINEAR          to fit linear (not log) intensity
Chelp    FIXCTR=k        0/1/2 for free/fixed/median centers
Chelp    ELLIP=e         Force ellipticity to the value e
Chelp    NITER=n         Number of iterations
Chelp    SCALE=s         image scale "/pixel
Chelp    SKY=s           set the sky value to s instead of 0
Chelp    TV              use/display on TV image
Chelp    NOTV            disable use of TV image
Chelp    OLD             continue interating with old parameters
Chelp    MODEL           replace image with a model from params
Chelp    RMSTAR          automatically ignore stars
Chelp    COS3X=k         0/1/2 use no/med/each cos3x in model
Chelp    COS3X < 0       use cos6x instead of cos3x
Chelp    COS4X=k         0/1/2 use no/med/each cos4x in model
Chelp    TIE=k           use kth order poly fit to each param
Chelp                        or smooth with |k| pts if k < 0
Chelp    AVG=n           averages a box "radius" n when
Chelp                        sampling data. n=2 gives a 5x5 box
Chelp    GAIN=g          adjust the "gain" of iterations, def=1
Chelp    GChelp          fit a globular cluster instead.
Chelp                    for this option, also give nr for
Chelp                    the number of radii within the
Chelp                    characteristic width
Chelp    EDIT            adjust de parameters
C (not implemented)     ALPHA=a         Force position angle to the value a

      include 'vistalink.inc'
      include 'imagelink.inc'
      include 'profile.inc'
      real data(ncol,nrow)

C       The profile calculations are held in the PRF common block.  The
C       parameters kept for each contour are as follows:
C
C               1       Semimajor axis a
C               2       Contour central x0 (row number)
C               3       Contour central y0 (column number)
C               4       Average surface brightness of contour
C               5       Position angle of contour, (PA CCW from top, deg)
C               6       Ellipticity of contour
C               7       N=3 amplitude relative to mean surface brightness
C               8       N=3 phase angle
C               9       N=4 amplitude relative to mean surface brightness
C              10       N=4 phase angle
C              11       Contour intensity derivative d logI / d logr
C       N_PRF           The number of contours
C       SCALE           The image scale ''/pixel

      parameter (maxrad=250, nflags=17)
      real flags(20), param(11,maxrad), buf(maxrad,3)
      character key
      character*8 parm
      character*80 line
      common /elltest/ ktest, itest, iverbose
C   Flags: (1) x0              Param: (1) r (semimajor axis a)
C          (2) y0                     (2) x0
C          (3) r0                     (3) y0
C          (4) r1                     (4) I(r=a)
C          (5) Nr                     (5) alpha (PA CCW from x=0, deg)
C          (6) Niter                  (6) epsilon (semiminor axis b = ea)
C          (7) rlaw 0/1/2 li/lo/rq    (7) I(3x)
C          (8) fitlog 0/1 li/lo I     (8) Theta(3x) (deg)
C          (9) fixctr 0/1 free x0,y0  (9) I(4x)
C         (10) terplaw               (10) Theta(4x) (deg)
C         (11) rmstar 0/1            (11) d logI / d logr
C         (12) old 0/1
C         (13) tie -1/k
C         (14) avg 0/n
C         (15) icos3
C         (16) ellip
C         (17) gain
      data niter /5/, ifixctr /0/, irlaw /2/, ifitlog /1/, iterplaw /0/
      data irmstar /0/, itv /0/, icos3 /2/, icos4 /2/, isky /0/
      data itie /-1/, navg /0/, iedit /0/, ellip /-1./
      data gain /1.0/

 6000 format(1x,a,$)

      if (.not. go) return

C       Initialize parameters and look for keywords

      q = 180/3.14159265
      ktest = -1
      itest = 0
      iverbose = 0
      iedit = 0
      iold = 0
C Load up old values for the parameters
      nrad = n_prf
      scale = prf_sc
      do 3 k = 1,nrad
         param(1,k) = param_prf(1,k)
         param(2,k) = param_prf(2,k) - isc
         param(3,k) = param_prf(3,k) - isr
         param(4,k) = param_prf(4,k)
         param(5,k) = param_prf(5,k) + 90
         param(6,k) = 1 - param_prf(6,k)
         param(7,k) = param_prf(7,k)
         param(8,k) = param_prf(8,k)
         param(9,k) = param_prf(9,k)
         param(10,k) = param_prf(10,k)
         param(11,k) = param_prf(11,k)
 3    continue
      do 4 k = 1,nflags
         flags(k) = param_prf(12,k)
 4    continue

      do 5 i=1, ncon
         if (word(i) .eq. 'OLD') iold = 1
 5    continue

      if(iold.eq.0) then
         nrad = 0
         niter = 5
         ifixctr = 0
         scale = 1.0
         x0 = -10000
         y0 = -10000
         r0 = -1
         r1 = -1
         irlaw = 2
         ifitlog = 1
         iterplaw = 0
         irmstar = 0
         itv = 0
         icos3 = 2
         icos4 = 2
         isky = 1
         sky = 0
         itie = -1
         navg = 0
         igc = 0
         ellip = -1
      else
         x0 = flags(1)
         y0 = flags(2)
         r0 = flags(3)
         r1 = flags(4)
         niter = flags(6)
         irlaw = flags(7)
         ifitlog = flags(8)
         ifixctr = flags(9)
         iterplaw = flags(10)
         irmstar = flags(11)
         itie = flags(13)
         navg = flags(14)
         icos3 = flags(15)
         ellip = flags(16)
      end if
      gain = 1
      imodel = 0

      do 10 i=1, ncon
         if (word(i) .eq. 'TV') itv = 1

         if (word(i) .eq. 'NOTV') itv = 0

         if (word(i) .eq. 'MODEL') imodel = 1

         if (word(i) .eq. 'LINEAR') ifitlog = 0

         if (word(i) .eq. 'TEST') itest = 1

         if (word(i) .eq. 'VERBOSE') iverbose = 1

         if (word(i) .eq. 'EDIT') iedit = 1

         if (word(i) .eq. 'GC') igc = 1

         if (word(i)(1:5) .eq. 'DUMP=') then
            call assign(word(i),f,parm)
            if (xerr) return
            ktest = nint(f)
         end if

         if (word(i)(1:4) .eq. 'AVG=') then
            call assign(word(i),f,parm)
            if (xerr) return
            navg = nint(f)
         end if

         if (word(i)(1:4) .eq. 'TIE=') then
            call assign(word(i),f,parm)
            if (xerr) return
            itie = nint(f)
         end if

         if (word(i)(1:3) .eq. 'NR=') then
            call assign(word(i),f,parm)
            if (xerr) return
            nrad = nint(f)
         end if

         if (word(i)(1:6) .eq. 'COS3X=') then
            call assign(word(i),f,parm)
            if (xerr) return
            icos3 = nint(f)
         end if

         if (word(i)(1:6) .eq. 'COS4X=') then
            call assign(word(i),f,parm)
            if (xerr) return
            icos4 = nint(f)
         end if

         if (word(i)(1:6) .eq. 'NITER=') then
            call assign(word(i),f,parm)
            if (xerr) return
            niter = nint(f)
         end if

         if (word(i)(1:5) .eq. 'RLAW=') then
            call assign(word(i),f,parm)
            if (xerr) return
            irlaw = nint(f)
         end if

         if (word(i) .eq. 'RMSTAR') irmstar = 1

         if (word(i)(1:7) .eq. 'FIXCTR=') then
            call assign(word(i),f,parm)
            if (xerr) return
            ifixctr = nint(f)
         end if

         if (word(i)(1:6) .eq. 'SCALE=') then
            call assign(word(i),scale,parm)
            if (xerr) return
         end if

         if (word(i)(1:4) .eq. 'SKY=') then
            call assign(word(i),sky,parm)
            if (xerr) return
            isky = 1
         end if

         if (word(i)(1:3) .eq. 'X0=') then
            call assign(word(i),x0,parm)
            if (xerr) return
         end if

         if (word(i)(1:3) .eq. 'Y0=') then
            call assign(word(i),y0,parm)
            if (xerr) return
         end if

         if (word(i)(1:3) .eq. 'R0=') then
            call assign(word(i),r0,parm)
            if (xerr) return
         end if

         if (word(i)(1:3) .eq. 'R1=') then
            call assign(word(i),r1,parm)
            if (xerr) return
         end if

         if (word(i)(1:6) .eq. 'ELLIP=') then
            call assign(word(i),f,parm)
            if (xerr) return
            ellip = f
         end if

         if (word(i)(1:5) .eq. 'GAIN=') then
            call assign(word(i),gain,parm)
            if (xerr) return
         end if

 10   continue


C Piss and moan if illegal parameters

      if(iedit.eq.1) then
 9       write(6,6000) 'Enter parameter# (or 0), isophote# (or -1): '
         call invista(line)
         read(line,*) i, k
         if(i.eq.0) return
         if(k.gt.0) then
            write(6,6000) 'Enter value for parameter: '
            call invista(line)
            read(line,*) value
            write(6,*) 'Changing ', param_prf(i,k), ' to', value
            param_prf(i,k) = value
         else
            write(6,6000) 'Enter A,B (par -> A*par+B): '
            call invista(line)
            read(line,*) apar, bpar
            do 5762 k = 1,nrad
               param_prf(i,k) = apar*param_prf(i,k) + bpar
 5762       continue
         end if
         goto 9
      end if

      if(x0.lt.-1000 .or. y0.lt.-1000) then
         if(itv.eq.1) then
            write(6,*) 'Place cursor at center; strike a key.'
            call mark(ir,ic,key)
            call tvcross(ir,ic)
            x0 = ic-isc
            y0 = ir-isr
         else
            write(6,*) 'X0=', x0, 'Y0=', y0, ' Center required...'
            return
         end if
      end if

      if(igc.eq.1) goto 100

      if(r0.lt.0 .or. r1.lt.0 .or. nrad.lt.2) then
         if(itv.eq.1) then
            write(6,*) 'Place cursor at inner radius; strike a key.'
            call mark(ir,ic,key)
            x1 = ic-isc
            y1 = ir-isr
            r0 = sqrt((x1-x0)*(x1-x0)+(y1-y0)*(y1-y0))
            call tvcirc(y0+isr,x0+isc,r0,0.0,0.0)
            write(6,*) 'Place cursor at outer radius; strike a key.'
            call mark(ir,ic,key)
            x1 = ic-isc
            y1 = ir-isr
            r1 = sqrt((x1-x0)*(x1-x0)+(y1-y0)*(y1-y0))
            call tvcirc(y0+isr,x0+isc,r1,0.0,0.0)
            if(nrad.lt.2) then
               write(6,6000) 'Enter number of ellipses to fit: '
               call invista(line)
               read(line,*) nrad
            end if
         else
            write(6,*) 'R0=', r0, 'R1=', r1, 'N=', nrad,
     $           ' Radius limits required...'
            return
         end if
      end if

      if(nrad.gt.maxrad) then
         write(6,*) 'Requested/maximum radii =', nrad, maxrad
         return
      end if

C      if(ifixctr.eq.2) then
C         do 12 k = 1,nrad
C            buf(k,1) = param(2,k)
C            buf(k,2) = param(3,k)
C 12      continue
C         x0 = amedian(nrad,buf(1,1))
C         y0 = amedian(nrad,buf(1,2))
C      end if

* Fit the data with model ellipses
      flags(1) = x0
      flags(2) = y0
      flags(3) = r0
      flags(4) = r1
      flags(5) = nrad
      flags(6) = niter
      flags(7) = irlaw
      flags(8) = ifitlog
      flags(9) = ifixctr
      flags(10) = iterplaw
      flags(11) = irmstar
      flags(12) = iold
      flags(13) = itie
      flags(14) = navg
      flags(15) = icos3
      flags(16) = ellip
      flags(17) = gain
      call fitprofile(isc,isr,flags,param,ncol,nrow,data)

* Fit a deVaucouleurs profile to the data
      do 20 k = 1,nrad
         buf(k,1) = param(1,k)
         buf(k,2) = param(1,k)*param(6,k)
         buf(k,3) = param(4,k)
 20   continue
      if(isky.eq.1) skymin = sky

      call dvfit(nrad,buf(1,1),buf(1,3),isky,reff,feff,sky)
      call dvfit(nrad,buf(1,2),buf(1,3),isky,remin,femin,skymin)
      write(6,2001) reff, remin, feff, femin, sky, skymin
 2001 format(1x,'Re =',2f8.1,4x,'Ie =',2f9.1,4x,'Sky =',2f9.1)

      IF(ITEST.EQ.1) THEN
         ALPHA = 7.669
         DO 21 K = 1,NRAD
            FIT = FEFF*EXP(ALPHA*(1-(PARAM(1,K)/REFF)**.25))
            WRITE(6,*) K, PARAM(1,K), PARAM(4,K), FIT+SKY
 21      CONTINUE
      END IF

* Display the elliptical contours, if requested
      if(itv.eq.1) then
         do 200 k = 1,nrad
            call tvcirc(param(3,k)+isr, param(2,k)+isc, param(1,k), 
     $           param(5,k)-90, 1-param(6,k))
C            write(6,*) k, param(1,k), sqrt(sqrt(param(1,k))), param(4,k)
 200     continue
      end if

* Fill in the profile parameters
      n_prf = nrad
      prf_sc = scale
      do 30 k = 1,nrad
         param_prf(1,k) = param(1,k)
         param_prf(2,k) = param(2,k) + isc
         param_prf(3,k) = param(3,k) + isr
         param_prf(4,k) = param(4,k)
         param_prf(5,k) = param(5,k) - 90
         param_prf(6,k) = 1 - param(6,k)
         param_prf(7,k) = param(7,k)
         param_prf(8,k) = param(8,k)
         param_prf(9,k) = param(9,k)
         param_prf(10,k) = param(10,k)
         param_prf(11,k) = param(11,k)
 30   continue
      do 31 k = 1,nflags
         param_prf(12,k) = flags(k)
 31   continue
      prf_head = headbuf(im)

* Replace the image with a synthetic image from the model, if requested
      if(imodel.eq.0) return

C We will not allow models to be fitted with sky values determined by
C DVFIT!.  Thus unless isky = 1, we force isky = 1 and then sky = 0!
C This is really a kludge, and should be straightened out someday!  It
C is especially important if we are to get reasonable results for the
C variation of mbar with radius!
      if(isky.ne.1) then
         isky = 1
         sky = 0
      end if

      call synthesize(nrad,param,reff,feff,sky,remin,femin,skymin,
     $     icos3,icos4,ncol,nrow,data,navg)

      goto 40

C Fit concentric circles to a globular cluster
C First find the center and width
 100  call arraycenter(ncol,nrow,xcent,ycent,xwidth,ywidth,data)
      if (xwidth.eq.0.or.ywidth.eq.0) then
         write (6,*) 'GC width error: xwidth/ywidth = ', xwidth,
     $        ywidth
         return
      else
         width = (xwidth + ywidth) / 2.0
      end if
C See if a fixed center is desired.
      if(ifixctr.ne.0) then
         xcent = x0
         ycent = y0
      endif


C GC parameters for each annulus:
C (1) r
C (2) x0 = xcent (same for each annulus)
C (3) y0 = ycent (same for each annulus)
C (4) I(r)
C (5) rms of I(r)
C (6) sum of pixels in this annulus
C (7) to (11) ignored

C Determine the number of annuli required and their spacing
      rmax = sqrt(float(ncol*ncol + nrow*nrow))
      nradtot = nint(nrad * sqrt(sqrt(rmax / width)))
      if (nradtot.gt.maxrad) then
         write(6,*) 'Too many radii: nradtot/maxrad =', nradtot,
     $        maxrad
         return
      end if

      do 101 i=1,nrad
         param(1,i) = i * width / nrad
 101  continue

      rqmax = sqrt(sqrt(rmax))
      do 102 i=nrad+1,nradtot
         param(1,i) = (i * rqmax / nradtot)**4
 102  continue

C Calculate the mean value of pixels in each annulus
C First, initialize params
      do 110 k=1,nradtot
         param(2,k) = xcent
         param(3,k) = ycent
         param(4,k) = 0.0
         param(5,k) = 0.0
         param(6,k) = 0.0
 110  continue

C Loop through all pixels; put each in proper annulus and count.
C For now, ignore data = 0.0
      do 113 i=1,ncol
         do 114 j=1,nrow
            rij = sqrt((i-xcent)*(i-xcent) + (j-ycent)*(j-ycent))
            do 115 k=1,nradtot
               if (rij.le.param(1,k)) then
                  if (data(i,j).ne.0.0) then
                     param(4,k) = param(4,k) + data(i,j)
                     param(5,k) = param(5,k) + data(i,j)*data(i,j)
                     param(6,k) = param(6,k) + 1.0
                  end if
                  goto 114
               end if
 115        continue
 114     continue
 113  continue

C Compute mean and error, write results.
C The radius listed here is the outer radius of the annulus, not the average
C radius which will be used to compute the synthetic image.
      write(6,*) 'xwidth = ', xwidth,  'ywidth = ', ywidth
      write(6,*) '  n    rad   xcent   ycent   intens     rms    npix'
      do 116 k=1,nradtot
         if (param(6,k).gt.0.0) then
            param(4,k) = param(4,k) / param(6,k)
            param(5,k) = sqrt((param(5,k) / param(6,k)
     $           - param(4,k) * param(4,k)) / param(6,k))
         end if
         write(6,1100) k, (param(i,k),i=1,6)
 1100    format(i4,f8.2,2f8.2,f9.1,f8.1,f9.1)
 116  continue

C Replace data with synthetic image if requested
      if (imodel.eq.0) return
      call makegcmodel(ncol,nrow,data,param,nradtot,nrad,xcent,ycent
     $     ,width)

 40   continue

      return
      end

      subroutine fitprofile(ix0,iy0,flags,par,nx,ny,data)
      parameter (pi=3.14159265, maxstep=360, maxrad=100)
      include 'vistalink.inc'
      real data(nx,ny)
      real flags(20), par(11,1)
      real contour(maxstep), fcoeff(9)
      real xfit(maxrad), yfit(maxrad), rms(maxrad), scale(2), lpoly
      real*8 coeff(8)
      common /elltest/ ktest, itest, iverbose
C   Flags: (1) x0              Param: (1) r (semimajor axis a)
C          (2) y0                     (2) x0
C          (3) r0                     (3) y0
C          (4) r1                     (4) I(r=a)
C          (5) Nr                     (5) alpha (PA CCW from x=0)
C          (6) Niter                  (6) epsilon (semiminor axis b = ea)
C          (7) rlaw 0/1/2 li/lo/rq    (7) I(3x)
C          (8) fitlog 0/1 li/lo I     (8) Theta(3x) (deg)
C          (9) fixctr 0/1 free x0,y0  (9) I(4x)
C         (10) terplaw               (10) Theta(4x) (deg)
C         (11) rmstar 0/1            (11) d logI / d logr
C         (12) old 0/1
C         (13) tie -1/k
C         (14) avg 0/n
C         (15) icos3
C         (16) ellip
C         (17) gain
      x0 = flags(1)
      y0 = flags(2)
      r0 = flags(3)
      r1 = flags(4)
      nrad = nint(flags(5))
      niter = nint(flags(6))
      irlaw = nint(flags(7))
      ifitlog = nint(flags(8))
      ifixctr = nint(flags(9))
      iterp = nint(flags(10))
      irmstar = nint(flags(11))
      iold = nint(flags(12))
      itie = nint(flags(13))
      navg = nint(flags(14))
      icos3 = nint(flags(15))
      ellip = flags(16)
      gain = flags(17)

      q = 180/pi

      if(iold.eq.1) goto 19

C Look at the half-way radius to get rough values for alpha
      r = 0.5*(r0+r1)
      do 11 i = 1,50
         theta = float(i-1)*pi/25
C         WRITE(6,*) I, THETA, IX, IY, DATA(IX,IY), ALPHA, TOP
         ix = min(nx,max(1,nint(r*cos(theta) + x0)+1))
         iy = min(ny,max(1,nint(r*sin(theta) + y0)+1))
         if(i.eq.1) top = data(ix,iy)
         if(data(ix,iy).ge.top) then
            top = data(ix,iy)
            alpha = theta
         end if
 11   continue
      if(alpha.gt.pi) alpha = alpha - pi
      if(alpha.lt.0) alpha = alpha + pi

C Run in at 90 deg to this angle to get a rough value for epsilon
      if(ellip.lt.0) then
         epsilon = 0
         do 12 ir = nint(r),6,-3
            ix = min(nx,max(1,nint(ir*cos(alpha+pi/2) + x0)+1))
            iy = min(ny,max(1,nint(ir*sin(alpha+pi/2) + y0)+1))
            if(data(ix,iy).ge.top) then
               epsilon = float(ir)/nint(r)
               goto 13
            end if
 12      continue
 13      continue
         if(epsilon.eq.0) epsilon = 1
      else
         epsilon = 1 - ellip
      end if

C Establish the values for the radii, and fill in initial parameters
      do 10 k = 1,nrad
         frac = float(k-1)/(nrad-1)
         if(irlaw.eq.0) then
            par(1,k) = r0 + frac*(r1-r0)
         else if(irlaw.eq.1) then
            par(1,k) = r0 * exp(frac*alog(r1/r0))
         else
            par(1,k) = (r0**0.25 + frac*(r1**0.25-r0**0.25))**4
         end if
         par(2,k) = x0
         par(3,k) = y0
         par(4,k) = 1000
         do 14 i = 1,10
            angle = alpha + 2.*pi*float(i-1)/10
            ix = min(nx,max(1,nint(par(1,k)*cos(angle) + x0)+1))
            iy = min(ny,max(1,nint(par(1,k)*sin(angle) + y0)+1))
            if(data(ix,iy).gt.0) then
               par(4,k) = data(ix,iy)
               goto 15
            end if
 14      continue
 15      continue
         par(5,k) = q*alpha
         par(6,k) = epsilon
         par(7,k) = 0
         par(8,k) = 0
         par(9,k) = 0
         par(10,k) = 0
         par(11,k) = -2
 10   continue

 19   continue
C      if(ifixctr.eq.2) then
C         do 17 k = 1,nrad
C            par(2,k) = x0
C            par(3,k) = y0
C 17      continue
C      end if

      if(iverbose.ne.0) then
         if(icos3.ge.0) then
            write(6,1001)
         else
            write(6,1002)
         end if
         do 18 k = 1,nrad
            write(6,1000) par(1,k),par(2,k)+ix0,par(3,k)+iy0,
     $           par(4,k),par(5,k)-90,1-par(6,k),(par(i,k),i=7,11)
 1000       format(f6.1,2f8.2,f8.0,f7.2,f6.3,2(f7.4,f7.2),f6.2)
 18      continue
      end if
 1001 format('   r      x0      y0      I0    alpha  ellip',
     $        ' I(3x)  A(3x)  I(4x)  A(4x) slope')
 1002 format('   r      x0      y0      I0    alpha  ellip',
     $        ' I(6x)  A(6x)  I(4x)  A(4x) slope')

C Iterate NITER times, improving estimates of contours
      do 100 n = 1,niter

C Loop over each contour
         do 110 k = 1,nrad
            if(NOGO) return

C Acquire new data describing the deviations as a function of theta
            nstep = min(maxstep,nint(pi*par(1,k)))
            call getcontour(par(1,k),iterp,nstep,contour,nx,ny,data,
     $           navg)

C If fitting logarithms, normalize by the value itself
            if(ifitlog.eq.1) then
               f0 = par(4,k)
               nfit = 0
               do 120 i = 1,nstep
                  clog = contour(i)/f0 + 1
                  if(clog.gt.0) then
                     contour(i) = alog(clog)
                     nfit = nfit + 1
                  else
                     contour(i) = -1e10
                  end if
 120           continue
            end if

C Trim it of stars and determine the rms of the intensity variations
            call trimit(nstep,contour,irmstar,rms(k))
            if(rms(k).gt.0) then
               rms(k) = 1/(rms(k)*rms(k))
            else
               rms(k) = 0
            end if

C Fit it with cos/sin(0-4)x
            call fitcontour(nstep,contour,icos3,fcoeff)

C            IF(K.EQ.KTEST.OR.NFIT.LT.9) THEN
            IF(K.EQ.KTEST) THEN
            DO 600 I = 1,NSTEP
               THETA = 2*PI*FLOAT(I-1)/NSTEP
               FIT = FCOEFF(1) + 
     $              FCOEFF(2)*COS(THETA) + FCOEFF(3)*SIN(THETA) +
     $              FCOEFF(4)*COS(2*THETA) + FCOEFF(5)*SIN(2*THETA) +
     $              FCOEFF(6)*COS(3*THETA) + FCOEFF(7)*SIN(3*THETA) +
     $              FCOEFF(8)*COS(4*THETA) + FCOEFF(9)*SIN(4*THETA)
               IF(IFITLOG.EQ.1) then
                  VALUE = CONTOUR(I) + ALOG(PAR(4,K))
               ELSE
                  VALUE = CONTOUR(I) + PAR(4,K)
               END IF
               WRITE(2,2001) I,PAR(MIN(12,I),K),
     $              THETA,CONTOUR(I),FIT,VALUE
 2001          FORMAT(I5,1P5G14.5)
 600        CONTINUE
            END IF

C            WRITE(6,'(9f8.5)') FCOEFF


C Alter the parameters to reflect the deviations of contour
            call alter(par(1,k),ifixctr,ifitlog,ellip,fcoeff,gain)

 110     continue

C Adjust the parameters to lie along a polynomial in r**1/4
C Be sure to fit log I...
         if(itie.ge.0) then
            do 122 k = 1,nrad
               xfit(k) = sqrt(sqrt(par(1,k)))
 122        continue
            do 123 j = 2,10
               do 124 k = 1,nrad
                  yfit(k) = par(j,k)
                  if(j.eq.4) yfit(k) = alog10(yfit(k))
 124           continue
               scale(1) = xfit(1)
               scale(2) = xfit(nrad)
               call fitwlpoly(nrad,xfit,yfit,rms,scale,itie+1,coeff)
               do 125 k = 1,nrad
                  par(j,k) = lpoly(xfit(k),scale,itie+1,coeff)
                  if(j.eq.4) par(j,k) = 10.**par(j,k)
 125             continue
 123          continue
         else if(itie.lt.-1) then
* Smooth the parameters a bit by (|tie|-1 k) binomial coefficients
* |tie| is therefore the number of points contributing to the smoothed data,
* and should be an odd number, so as to be symmetric about the center.
            do 126 j = 2,10
               do 127 k = 1,nrad
                  yfit(k) = par(j,k)
                  if(j.eq.4) yfit(k) = alog10(yfit(k))
 127           continue
               do 128 k = 1,nrad
                  par(j,k) = 0
                  do 129 i = 0,iabs(itie)-1
                     f = bc(iabs(itie)-1,i)
                     k1 = k + i - iabs(itie)/2
                     k2 = k - i + iabs(itie)/2
                     if(k1.lt.1.or.k1.gt.nrad .or.
     $                    k2.lt.1.or.k2.gt.nrad) k1 = k
                     par(j,k) = par(j,k) + f * yfit(k1)
 129              continue
                  if(j.eq.4) par(j,k) = 10.**par(j,k)
 128           continue
 126        continue

         end if

* Set the center to the median of all the points if requested
         if(ifixctr.eq.2) then
            do 121 k = 1,nrad
               xfit(k) = par(2,k)
               yfit(k) = par(3,k)
 121        continue
            x0 = amedian(nrad,xfit)
            y0 = amedian(nrad,yfit)
            do 1211 k = 1,nrad
               par(2,k) = x0
               par(3,k) = y0
 1211       continue
         end if

C Improve the estimates of d logI / d logr
         if(n.eq.niter.or.iverbose.ne.0) then
            if(icos3.ge.0) then
               write(6,1001)
            else
               write(6,1002)
            end if
         end if
         do 130 k = 1,nrad
            k1 = max(1,k-1)
            k2 = min(nrad,k+1)
            par(11,k) = (par(4,k1)-par(4,k2))/par(4,k) * 
     $           par(1,k)/(par(1,k1)-par(1,k2))
C We will NOT accept non-monotonic decreasing profiles
            if(par(11,k).gt.0) then
               par(11,k) = -2
               write(6,*) 'dlogI/dlogr forced to -2 at k =', k
            end if
C Tell us about the latest...
            if(n.eq.niter.or.iverbose.ne.0) then
               write(6,1000) par(1,k),par(2,k)+ix0,par(3,k)+iy0,
     $              par(4,k),par(5,k)-90,1-par(6,k),(par(i,k),i=7,11)
            end if
 130     continue
 100  continue

      IF(KTEST.GT.0) CLOSE(2)


      return
      end

      subroutine getcontour(par,iterp,nstep,contour,nx,ny,data,navg)
      parameter (pi=3.14159265)
      real contour(nstep), data(nx,ny), par(11)
C Fill in the contour array at evenly spaced theta
C Use DATA = 0 as a flag for non-existent data
C For the time being, ignore ITERP 
* Keep compiler happy
      if(iterp.eq.0) i=0
      q = 180/pi
      r = par(1)
      x0 = par(2)
      y0 = par(3)
      f0 = par(4)
      alpha = par(5)/q
      epsilon = par(6)
      ca = cos(alpha)
      sa = sin(alpha)
      do 10 i = 1,nstep
         theta = 2*pi*float(i-1)/nstep
         xp = r*cos(theta)
         yp = epsilon*r*sin(theta)
         x = +xp*ca - yp*sa + x0
         y = +xp*sa + yp*ca + y0
         ix = nint(x)
         iy = nint(y)
         if((ix-navg).lt.1.or.(ix+navg).ge.nx .or.
     $        (iy-navg).lt.1.or.(iy+navg).ge.ny) then
            contour(i) = -1e10
            goto 10
         end if
C If navg = 0, get the contour the original way ...
         if(navg.eq.0) then
C Use DATA = 0 as a flag for non-existent data
            if(data(ix,iy).eq.0 .or. data(ix+1,iy).eq.0 .or.
     $           data(ix,iy+1).eq.0 .or. data(ix+1,iy+1).eq.0) then
               contour(i) = -1e10
               goto 10
            end if
C Use bilinear interpolation of the four adjacent pixels bounding (X,Y)
C Use X(Y) = IX(Y)-0.5 for exact center of pixel DATA(IX,IY)
            contour(i) = -f0 + 
     $           (x-ix+0.5)*(y-iy+0.5)*data(ix+1,iy+1) + 
     $           (ix+0.5-x)*(y-iy+0.5)*data(ix,iy+1) + 
     $           (x-ix+0.5)*(iy+0.5-y)*data(ix+1,iy) + 
     $           (ix+0.5-x)*(iy+0.5-y)*data(ix,iy)
            goto 10
         endif
C Otherwise, when navg > 0, use a (2*navg + 1)^2 array ...
C   ntot    = total number of weights
C   nbadtot = total number of weights omitted from average
         ntot = 0
         nbadtot = 0
         pixtot = 0
         do 11 j = -navg,navg
            do 12 k= -navg,navg
               nwght = 2*(2*navg - iabs(j) - iabs(k)) + 1
               ntot = ntot + nwght
               if (data(ix+j,iy+k).eq.0) then
                  nbadtot = nbadtot + nwght
               else
                  pixtot = pixtot + nwght * data(ix+j,iy+k)
               endif
 12         continue
 11      continue
C Omit a contour if more than 20% of the weights are bad.
         if (float(nbadtot)/ntot.le.0.2) then
            contour(i) = pixtot/(ntot-nbadtot) - f0
         else
            contour(i) = -1e10
            write(6,*) 'GETCONTOUR: omitted contour(i), nbadtot/ntot=',
     $           nbadtot,ntot
         endif
 10   continue
         
      return
      end

      subroutine trimit(nstep,contour,irmstar,rms)
* Points = -1e10 are to be ignored.
* If IRMSTAR = 1, chop all points bigger than QFACTOR*(quartile-median)+median
* as well as all neighbors within NEIGH, mark as -9e9
* Return the rms of the resulting contour
      parameter (qfactor=4,neigh=2)
      real contour(nstep)
      real buf(360)
      real*8 ave, var

      if(irmstar.eq.1) then
* Accumulate points for sorting
         npt = 0
         do 10 i = 1,min(nstep,360)
            if(contour(i).gt.-1e9) then
               npt = npt + 1
               buf(npt) = contour(i)
            end if
 10      continue
* Use amedian to do the sorting
         amed = amedian(npt,buf)
         upperquart = buf((3*npt+2)/4)
         cut = qfactor*(upperquart-amed) + amed
         
* Cut out all contaminated points
         do 11 i = 1,nstep
            if(contour(i).gt.cut) then
               k0 = max(1,i-neigh)
               k1 = min(nstep,i+neigh)
* Don't chop points that will get nailed on the next iteration
               if(k1.lt.nstep.and.contour(i+1).gt.cut) k1 = i
               do 12 k = k0,k1
                  contour(i) = -9e9
 12            continue
            end if
 11      continue
      end if

      nused = 0
      ave = 0
      var = 0
      do 20 i = 1,nstep
         if(contour(i).gt.-1e9) then
            nused = nused + 1
            ave = ave + contour(i)
            var = var + contour(i)*contour(i)
         end if
 20   continue
      if(nused.gt.0) then
         ave = ave / nused
         var = var / nused - ave*ave
      end if
      rms = dsqrt(var)
      return
      end

      subroutine fitcontour(nstep,contour,icos3,fcoeff)
      parameter (pi=3.14159265)
      parameter (nterm=9)
      real contour(nstep), fcoeff(nterm)
      real v(nterm), term(nterm), a(nterm,nterm)
C Do a least squares fit of cos/sin(0-4)x
C ICOS3 >= 0:
C contour = p1 + p2*cosx + p3*sinx + p4*cos2x + p5*sin2x + 
C                                    p6*cos3x + p7*sin3x + p8*cos4x + p9*sin4x
C ICOS3 < 0:
C contour = p1 + p2*cosx + p3*sinx + p4*cos2x + p5*sin2x + 
C                                    p6*cos6x + p7*sin6x + p8*cos4x + p9*sin4x
      skip = -1e5

      do 10 j = 1,nterm
         v(j) = 0.
         do 11 i = 1,nterm
            a(i,j) = 0.
 11      continue
 10   continue

C Accumulate sums
      term(1) = 1.
      nused = 0
      do 20 j = 1,nstep
         if(contour(j).lt.skip) goto 20
         theta = 2*pi*float(j-1)/nstep
         term(2) = cos(theta)
         term(3) = sin(theta)
C I.e. cos(2*theta), sin(2*theta)
         term(4) = 2*term(2)*term(2) - 1
         term(5) = 2*term(2)*term(3)
C I.e. cos(4*theta), sin(4*theta)
         term(8) = 2*term(4)*term(4) - 1
         term(9) = 2*term(4)*term(5)
         if(icos3.ge.0) then
C I.e. cos(3*theta), sin(3*theta)
            term(6) = term(2)*term(4) - term(3)*term(5)
            term(7) = term(3)*term(4) + term(2)*term(5)
         else
C I.e. cos(6*theta), sin(6*theta)
            term(6) = term(4)*term(8) - term(5)*term(9)
            term(7) = term(5)*term(8) + term(4)*term(9)
         end if

         do 22 l = 1,nterm
            v(l) = v(l) + contour(j)*term(l)
            do 23 k = 1,l
               a(k,l) = a(k,l) + term(k)*term(l)
 23         continue
 22      continue
         nused = nused + 1
 20   continue


C Quit if insufficient points
 33   continue
      if(nused.lt.nterm) then
         do 32 i = 1,nterm
            fcoeff(i) = 0
 32      continue
         write(6,*) 'FITCONTOUR: quitting, nused = ',nused
         return
      end if

C Fill in symmetrical matrix
      do 30 l = 1,nterm-1
         do 31 k = l+1,nterm
            a(k,l) = a(l,k)
 31      continue
 30   continue

C Solve matrix by gaussian elimination
      do 40 j = 1,nterm-1
         do 41 i = j+1,nterm
            if(a(j,j).eq.0) then
               nused = 0
               goto 33
            end if
            r = a(i,j) / a(j,j)
            v(i) = v(i) - r*v(j)
            do 42 k = j+1,nterm
               a(i,k) = a(i,k) - r*a(j,k)
 42         continue
 41      continue
 40   continue

C Back substitute to solve for parameters
      fcoeff(nterm) = v(nterm) / a(nterm,nterm)
      do 50 i = 1,nterm-1
         j = nterm - i
         fcoeff(j) = v(j)
         do 51 k = j+1,nterm
            fcoeff(j) = fcoeff(j) - a(j,k)*fcoeff(k)
 51      continue
         fcoeff(j) = fcoeff(j) / a(j,j)
 50   continue
      return
      end

      subroutine alter(par,ifixctr,ifitlog,ellip,fcoeff,gain)
      parameter (pi=3.14159265)
      real par(11), fcoeff(9)
      q = 180/pi
      r = par(1)
      x0 = par(2)
      y0 = par(3)
      f0 = par(4)
      alpha = par(5) / q
      epsilon = par(6)

      dfdr = par(11) / r
      if(ifitlog.eq.0) dfdr = dfdr * f0

      if(ifixctr.ne.1) then
         dx0 = -fcoeff(2) / dfdr
         dy0 = -fcoeff(3) / dfdr * epsilon
         x0 = x0 + gain*(dx0 * cos(alpha) - dy0 * sin(alpha))
         y0 = y0 + gain*(dx0 * sin(alpha) + dy0 * cos(alpha))
      end if
      
      if(ellip.lt.0) then
         epsilon = epsilon + gain*2*epsilon*fcoeff(4)/(dfdr*r)
         if(epsilon.gt.1) epsilon = 1/epsilon
      else
         epsilon = 1 - ellip
      end if
      alpha = alpha - gain*2/(1/epsilon-epsilon)*fcoeff(5)/(dfdr*r)
      if(ifitlog.eq.0) then
         f0 = f0 + gain*(fcoeff(1) + fcoeff(4))
      else
         f0 = f0 * exp(gain*(fcoeff(1)+fcoeff(4)))
      end if

      par(2) = x0
      par(3) = y0
      par(4) = f0
      par(5) = q*alpha
      par(5) = amodder(par(5),90.,180.)
      par(6) = epsilon
      par(8) = q/3*atan2(fcoeff(7),fcoeff(6))
      par(8) = amodder(par(8),0.,120.)
      ampl3 = sqrt(fcoeff(6)*fcoeff(6) + fcoeff(7)*fcoeff(7))
      par(10) = q/4*atan2(fcoeff(9),fcoeff(8))
      par(10) = amodder(par(10),0.,90.)
      ampl4 = sqrt(fcoeff(8)*fcoeff(8) + fcoeff(9)*fcoeff(9))
      if(ifitlog.eq.0) then
         par(7) = ampl3/f0
         par(9) = ampl4/f0
      else
         par(7) = exp(ampl3) - 1
         par(9) = exp(ampl4) - 1
      end if
      return
      end

      function amodder(x,x0,dx)
C Return MOD(X-X0,DX) + X0, with due respect for x < 0.
      z = x - x0
      if(x.lt.x0) z = z + dx*(int((x0-x)/dx)+1)
      amodder = x0 + z - dx * int(z/dx)
      return
      end

      subroutine dvfit(n,r,f,isky,re,f0,skyfit)
* Program to fit a deVaucouleurs model to data
      parameter (maxpt=300, maxiter=50)
      real r(n), x(maxpt), f(n), y(maxpt)
      real rms(maxiter), sky(maxiter)
      common /elltest/ ktest, itest, iverbose

      if(n.gt.maxpt) then
         write(6,*) 'DEVAUC: insufficient array space', n
         return
      end if

      do 10 i = 1,n
         x(i) = sqrt(sqrt(r(i)))
 10   continue

      n1 = 1
* For seeing-flattened center's sake avoid the first few points if possible
      if(n.gt.10) n1 = n/5
* If isky = 1, adopt the given sky value, fit and exit...
      if(isky.eq.1) then
         iquit = 1
      else
         iquit = 0
         skyfit = 0
      end if

      nsky = 0
      do 20 k = 1,maxiter
         do 21 i = 1,n
            y(i) = alog(f(i)-skyfit)
 21      continue
         call linfit(n-n1+1,x(n1),y(n1),a,b,da,db,rfit,rmsfit)

         nsky = nsky + 1

         if(nsky.le.3) then
            sky(nsky) = skyfit
            rms(nsky) = rmsfit
         else
            if(rmsfit.lt.rms(2).eqv.skyfit.lt.sky(2)) then
               sky(nsky) = sky(3)
               rms(nsky) = rms(3)
               if(skyfit.lt.sky(2)) then
                  sky(3) = sky(2)
                  rms(3) = rms(2)
                  sky(2) = skyfit
                  rms(2) = rmsfit
               else
                  sky(3) = skyfit
                  rms(3) = rmsfit
               end if
            else
               sky(nsky) = sky(1)
               rms(nsky) = rms(1)
               if(skyfit.lt.sky(2)) then
                  sky(1) = skyfit
                  rms(1) = rmsfit
               else
                  sky(1) = sky(2)
                  rms(1) = rms(2)
                  sky(2) = skyfit
                  rms(2) = rmsfit
               end if
            end if
         end if

* tell us about it
         IF(ITEST.EQ.1) THEN
            WRITE(6,1000) N1, N, A, B, SKYFIT, RFIT, RMSFIT
 1000       FORMAT(2I4,2F10.3,F10.2,F10.6,F10.4)
         END IF

         if(iquit.eq.1) goto 25

* Decide whether to increase n1 to remove inner points from use
         if(a*x(n1)+b-y(n1).gt.2*rmsfit) then
            n1 = n1 + 1
            nsky = 0
         end if

* Improve the estimate for sky. Insist on always bracketing the minimum...
         if(nsky.eq.0) then
            skyfit = 0
         else if(nsky.eq.1) then
            skyfit = 0.5*f(n)
         else if(nsky.eq.2) then
            skyfit = 0.999*f(n)
         else
            if(rms(2).gt.amax1(rms(1),rms(3))) then
               write(6,*) 'DVFIT: non-monotonic rms(sky)! Quitting...'
               goto 25
            else if(rms(2).lt.amin1(rms(1),rms(3))) then
               skyfit = (rms(1)*(sky(3)*sky(3)-sky(2)*sky(2)) +
     $                   rms(2)*(sky(1)*sky(1)-sky(3)*sky(3)) + 
     $                   rms(3)*(sky(2)*sky(2)-sky(1)*sky(1))) / 
     $                  (2*(rms(1)*(sky(3)-sky(2)) + 
     $                      rms(2)*(sky(1)-sky(3)) + 
     $                      rms(3)*(sky(2)-sky(1))))
            else if(rms(2).lt.rms(1)) then
               skyfit = 0.5*(sky(2)+sky(3))
            else
               skyfit = 0.5*(sky(1)+sky(2))
            end if
         end if

* Quit when three points all agree to a relative rms variation of 1e-4
         if(nsky.ge.3 .and. (sky(3)-sky(1))/sky(2).lt.1e-4) then
            iquit = 1
            skyfit = sky(2)
         end if

 20   continue
 25   continue

* Calculate re, f0 = f(re); ln(f-sky) = ln(f0) + 7.669(1-(r/re)**1/4) = a*x + b
      alpha = 7.669
      f0 = exp(b-alpha)
      re = (alpha/a)**4

      return
      end
      
      subroutine olddvfit(n,r,f,isky,re,f0,sky)
* Program to fit a deVaucouleurs model to data
      parameter (maxpt=300, maxiter=20)
      real r(n), x(maxpt), f(n), y(maxpt)
      real rmsave(maxiter), skysave(maxiter)
      common /elltest/ ktest, itest, iverbose

      if(n.gt.maxpt) then
         write(6,*) 'DEVAUC: insufficient array space', n
         return
      end if

      do 10 i = 1,n
         x(i) = sqrt(sqrt(r(i)))
 10   continue

      n1 = 1
* For paranoia's sake avoid the first few points if possible
      if(n.gt.10) n1 = n/5
* If isky = 1, adopt the given sky value, fit and exit...
      if(isky.eq.1) then
         iquit = 1
      else
         iquit = 0
         sky = f(n) / 2
      end if

      nsky = 0
      do 20 k = 1,maxiter
         do 21 i = 1,n
            y(i) = alog(f(i)-sky)
 21      continue
         call linfit(n-n1+1,x(n1),y(n1),a,b,da,db,rfit,rms)

         nsky = nsky + 1
         skysave(nsky) = sky
         rmsave(nsky) = rms

* tell us about it
         IF(ITEST.EQ.1) THEN
            WRITE(6,1000) N1, N, A, B, SKY, RFIT, RMS
 1000       FORMAT(2I4,2F10.3,F10.2,F10.6,F10.4)
         END IF

         if(iquit.eq.1) goto 25

* Improve the estimate for sky...
         if(nsky.eq.1) then
            sky = sky * exp(y(n) - (a*x(n)+b))
         else if(nsky.eq.2) then
            if(rmsave(2).lt.rmsave(1)) then
               sky = 2*skysave(2)-skysave(1)
            else
               sky = 2*skysave(1)-skysave(2)
            end if
         else
* If rms doesn't make it into the top 3, halve the step that brought us to sky
            if(rmsave(nsky).gt.rmsave(3)) then
               sky = 0.5*(sky+skysave(1))
            else
               sky = quadmin(nsky,skysave,rmsave)
            end if
         end if

         if(sky.gt.f(n)) sky = y(n)*(1.-1./k)

* Decide whether to increase n1 to remove inner points from use
         if(a*x(n1)+b-y(n1).gt.2*rms) then
            n1 = n1 + 1
            nsky = 0
         end if

* Quit when three points all agree to a relative rms variation of 1e-4
         if(nsky.ge.3 .and. 
     $        abs(rmsave(1)-rmsave(3))/rmsave(1).lt.1e-4) then
            iquit = 1
            sky = skysave(1)
         end if

 20   continue
 25   continue

* Calculate re, f0 = f(re); ln(f-sky) = ln(f0) + 7.669(1-(r/re)**1/4) = a*x + b
      alpha = 7.669
      f0 = exp(b-alpha)
      re = (alpha/a)**4

      return
      end
      
      function quadmin(n,x,y)
* Find the lowest y values and return the xmin value from a parabola fit
* Keep the x, y arrays sorted
      real x(n), y(n)
      do 11 j = 2,n
         yn = y(j)
         xn = x(j)
         do 10 i = j-1,1,-1
            if(yn.lt.y(i)) then
               x(i+1) = x(i)
               y(i+1) = y(i)
               x(i) = xn
               y(i) = yn
            end if
 10      continue
 11   continue
* See whether we have straddled a minimum or whether it is to the side
      xn = amin1(x(2),x(3))
      xp = amax1(x(2),x(3))
      quadmin = (y(1)*(x(3)*x(3)-x(2)*x(2)) +
     $     y(2)*(x(1)*x(1)-x(3)*x(3)) + y(3)*(x(2)*x(2)-x(1)*x(1))) / 
     $     (2*(y(1)*(x(3)-x(2)) + y(2)*(x(1)-x(3)) + y(3)*(x(2)-x(1))))
* Repair bad guesses
      WRITE(6,*) X(1), X(2), X(3), Y(1), Y(2), Y(3), QUADMIN
      if((x(1).lt.xn .and. quadmin.gt.xn) .or.
     $     (x(1).gt.xp .and. quadmin.lt.xp) .or.
     $     (x(1).gt.xn.and.x(1).lt.xp .and. 
     $     (quadmin.gt.xp .or. quadmin.lt.xn))) then
         quadmin = 1.5*x(1) - 0.5*x(2)
      end if
      WRITE(6,*) XN, XP, X(1), QUADMIN
      return
      end
      
      subroutine linfit(n,x,y,a,b,da,db,r,rms)
*     Program to compute brainless least squares linear fit to data
      implicit real*8 (a-h,o-z)
      real x(2), y(2), a, b, da, db, r, rms
      if(n.lt.2) return
      if(n.eq.2) then
         a = (y(2)-y(1))/(x(2)-x(1))
         b = y(1) - a*x(1)
         rms = 0
         return
      end if
      sx = 0
      sx2 = 0
      sy = 0
      sy2 = 0
      sxy = 0
      do 20 j = 1,n
         sx = sx + x(j)
         sx2 = sx2 + x(j)*x(j)
         sy = sy + y(j)
         sy2 = sy2 + y(j)*y(j)
         sxy = sxy + x(j)*y(j)
 20   continue
* First, consider x independent
      deltax = n*sx2 - sx*sx
      ax = (n*sxy - sx*sy) / deltax
      bx = (sx2*sy - sx*sxy) / deltax
      dy = dlinsqrt((sy2 + ax*ax*sx2 + bx*bx*n - 
     $     2*ax*sxy + 2*ax*bx*sx - 2*bx*sy) / (n-2))
      dax = dlinsqrt(n*dy*dy/deltax)
      dbx = dlinsqrt(dy*dy*sx2/deltax)
      
* Next, consider y independent
      deltay = n*sxy - sx*sy
      ay = (n*sy2 - sy*sy) / deltay
      by = (sxy*sy - sy2*sx) / deltay
      dx = dlinsqrt((sx2 + sy2/ay/ay + by*by/ay/ay*n -
     $     2/ay*sxy + 2*by/ay*sx - 2*by/ay/ay*sy) / (n-2))
      day = dlinsqrt(n*dx*dx*ay*ay*ay/deltay)
      dby = dlinsqrt((-by*sx+sxy)*dx*dx*ay*ay/deltay)
      
* Compute average slope and intercept
      aboth = dtan(.5*(datan(ax) + datan(ay)))
      bboth = (ax*by - ay*bx + a*(bx - by)) / (ax - ay)
      daboth = .5*(dax + day)
      dbboth = .5*(dbx + dby)
      corcof = (n*sxy-sx*sy)/dsqrt((n*sx2-sx*sx)*(n*sy2-sy*sy))
      
* For this purpose, return x independent and rms about the fit
      a = ax
      b = bx
      da = dax
      db= dbx
      r = corcof
      rms = dy

*     Print it out
C      WRITE(6,3000) N
C 3000 FORMAT(1X,I3,' points.'/)
C      WRITE(6,2000) DY
C 2000 FORMAT(1X,' x independent:   scatter in y =',F9.4)
C      WRITE(6,1000) AX, DAX, BX, DBX
C      WRITE(6,2001) DX
C 2001 FORMAT(1X,' y independent:   scatter in x =',F9.4)
C      WRITE(6,1000) AY, DAY, BY, DBY
C      WRITE(6,2002)
C 2002 FORMAT(1X,' mean relation:')
C      WRITE(6,1000) ABOTH, DABOTH, BBOTH, DBBOTH
C 1000 FORMAT(1X,'y =',F12.4,' (+/-',F10.4,')   x   + ',
C 1    F12.4,' (+/-',F10.4,')'/)
      return
      end

      function dlinsqrt(x)
      implicit real*8 (a-h,o-z)
      if(x.le.0) then
         dlinsqrt = 0
      else
         dlinsqrt = dsqrt(x)
      end if
      return
      end

      subroutine synthesize(n,par,re,fe,skye,rm,fm,skym,
     $     icos3,icos4,nx,ny,data,navg)
      parameter (pi=3.14159265, maxr=360, third=0.33333333, maxiter=10)
      real data(nx,ny)
      real contour(maxr)
      real par(11,1)
      real r(0:maxr), x0(0:maxr), y0(0:maxr), f0(0:maxr)
      real eps(0:maxr), ca(0:maxr), sa(0:maxr), rq(0:maxr)
      real c3(0:maxr), s3(0:maxr), c4(0:maxr), s4(0:maxr)
      real th(0:maxr), dth(0:maxr)
      logical inside, outside, incr
      integer counter_666 
      common /elltest/ ktest, itest, iverbose
      common /ellizero/ x0z,x1z,y0z,y1z,thz,dtz,ez0,ez1,r0z,r1z,
     $     xpt,ypt,x0mid,y0mid,camid,samid,epsmid,xp,yp,rmid, neval
      external elliterp

C     Flags: (1) x0              Param: (1) r (semimajor axis a)
C          (2) y0                     (2) x0
C          (3) r0                     (3) y0
C          (4) r1                     (4) I(r=a)
C          (5) Nr                     (5) alpha (PA CCW from x=0)
C          (6) Niter                  (6) epsilon (semiminor axis b = ea)
C          (7) rlaw 0/1/2 li/lo/rq    (7) I(3x)
C          (8) fitlog 0/1 li/lo I     (8) Theta(3x) (deg)
C          (9) fixctr 0/1 free x0,y0  (9) I(4x)
C         (10) terplaw               (10) Theta(4x) (deg)
C         (11) rmstar 0/1            (11) d logI / d logr
C         (12) old 0/1
      if(n+1.gt.maxr) then
         write(6,*) 'Synthesize: insufficient array space', n
         return
      end if
      write(6,*) 'Synthesize image...', nx, ' by ', ny
      q = 180/pi

* Find the most distant corner...
      rn = par(1,n)
      x0n = par(2,n)
      y0n = par(3,n)
      epsn = par(6,n)
      can = cos(par(5,n)/q)
      san = sin(par(5,n)/q)
      rho = 0
      x = 1 - 0.5
      y = 1 - 0.5
      xp = +(x-x0n)*can + (y-y0n)*san
      yp = -(x-x0n)*san + (y-y0n)*can
      rho = amax1(rho,xp*xp + yp*yp/(epsn*epsn))
      y = ny - 0.5
      xp = +(x-x0n)*can + (y-y0n)*san
      yp = -(x-x0n)*san + (y-y0n)*can
      rho = amax1(rho,xp*xp + yp*yp/(epsn*epsn))
      x = nx - 0.5
      xp = +(x-x0n)*can + (y-y0n)*san
      yp = -(x-x0n)*san + (y-y0n)*can
      rho = amax1(rho,xp*xp + yp*yp/(epsn*epsn))
      y = 1 - 0.5
      xp = +(x-x0n)*can + (y-y0n)*san
      yp = -(x-x0n)*san + (y-y0n)*can
      rho = amax1(rho,xp*xp + yp*yp/(epsn*epsn))
      router = sqrt(rho)

* Get a contour just inside the corners to see where the data is      
      par(1,n) = 0.95 * router
      call getcontour(par(1,n),0,maxr,contour,nx,ny,data,navg)
      par(1,n) = rn
      ave = 0
      nave = 0
      do 464 i = 1,maxr
         if(contour(i).gt.-1e5) then
            ave = ave + contour(i)
            nave = nave + 1
         end if
 464  continue
      if(nave.eq.0) then
         write(6,*) 0.95*router, ' catches no points'
         ave = par(4,n)
      else
         ave = ave / nave
      end if

      fn = par(4,n) + ave
C      sky = amin1(skye,0.98*fn)
      sky = skye
      flog = alog(fn-sky)
      epsilon = eps(n)
      rmajor = 1.05*router
* This is a BAAAAD point to return to, but if rmajor is screwed up, we have to.
      counter_666 = 1
 666  continue

      do 5 i = 1,n
         r(i) = par(1,i)
         rq(i) = sqrt(sqrt(r(i)))
         x0(i) = par(2,i)
         y0(i) = par(3,i)
         f0(i) = alog(par(4,i)-sky)
         eps(i) = par(6,i)
         th(i) = par(5,i)/q
* Prevent any PA jumps bigger than pi/2
         if(i.gt.1) then
            dtheta = pi*anint((th(i)-th(i-1))/pi)
            th(i) = th(i) - dtheta
            dth(i) = th(i) - th(i-1)
         else
            dtheta = 0
         end if
         ca(i) = cos(th(i))
         sa(i) = sin(th(i))
         c3(i) = par(7,i)*cos(3*(par(8,i)/q+dtheta))
         s3(i) = par(7,i)*sin(3*(par(8,i)/q+dtheta))
         c4(i) = par(9,i)*cos(4*par(10,i)/q)
         s4(i) = par(9,i)*sin(4*par(10,i)/q)
 5    continue

* If median cos3 or cos4 requested, construct the median parameters
      if(iabs(icos3).eq.1) then
         c3med = amedian(n,c3(1))
         s3med = amedian(n,s3(1))
         write(6,2023) sqrt(c3med**2+s3med**2), q/3*atan2(s3med,c3med)
 2023    format('Using I =',f8.5,' and A =',f6.1,' for cos3x')
      end if
      if(icos4.eq.1) then
         c4med = amedian(n,c4(1))
         s4med = amedian(n,s4(1))
         write(6,2024) sqrt(c4med**2+s4med**2), q/4*atan2(s4med,c4med)
 2024    format('Using I =',f8.5,' and A =',f6.1,' for cos4x')
      end if

* To avoid extrapolation, construct an inside isophote at r = 0
      r(0) = 0
      rq(0) = 0
      x0(0) = x0(1)
      y0(0) = y0(1)
      f0(0) = f0(1) - rq(1)*(f0(2)-f0(1))/(rq(2)-rq(1))
      eps(0) = eps(1)
      th(0) = th(1)
      dth(1) = 0
      ca(0) = ca(1)
      sa(0) = sa(1)
      c3(0) = c3(1)
      s3(0) = s3(1)
      c4(0) = c4(1)
      s4(0) = s4(1)
* Create an outside isophote which encompasses the entire picture.
* Insist that it conform to both the minor and major axis dvlaw fits.
      r(n+1) = rmajor
      rq(n+1) = sqrt(sqrt(r(n+1)))
      x0(n+1) = x0(n)
      y0(n+1) = y0(n)
      th(n+1) = th(n)
      dth(n+1) = 0
      ca(n+1) = ca(n)
      sa(n+1) = sa(n)
      c3(n+1) = c3(n)
      s3(n+1) = s3(n)
      c4(n+1) = c4(n)
      s4(n+1) = s4(n)

* Well... flog as computed above from a corner doesn't work very well at all

* But this attempt to adjust flog and epsilon from our r**1/4 fits is worse
      epsilon = eps(n)
      if(1.eq.1) goto 463
      rmajor = 1.01 * router
      rminor = epsilon*rmajor
      fmajor = fe*exp(7.699*(1-sqrt(sqrt(rmajor/re)))) + sky
      fminor = fm*exp(7.699*(1-sqrt(sqrt(rminor/rm)))) + skym
      flog = alog(sqrt(fmajor*fminor)-sqrt(sky*skym))
      if(fmajor.lt.fminor.and.fmajor.gt.skym) then
         rminor = rm * (1-alog((fmajor-skym)/fm)/7.669)**4
         epsilon = rminor / rmajor
         if(fmajor.gt.sky) then
            flog = alog(fmajor-sky)
         else
            flog = alog(fmajor-skym)
         end if
      else if(fminor.lt.fmajor.and.fminor.gt.sky) then
         rmajor = re * (1-alog((fminor-sky)/fe)/7.669)**4
         epsilon = rminor / rmajor
         flog = alog(fminor-sky)
      end if
 463  continue

* Therefore let's cross our fingers and extrapolate flog from the outer
* two isophotes.  What the hell, let's extrapolate epsilon as well...
* No, that's too dangerous; just average the outer two.
      frac = (rq(n+1)-rq(n-1)) / (rq(n)-rq(n-1))
      flog = f0(n-1) + frac*(f0(n)-f0(n-1))
C      epsilon = eps(n-1) + frac*(eps(n)-eps(n-1))
      epsilon = 0.5*(eps(n-1) + eps(n))



      write(6,6725) rmajor, exp(flog), sky, epsilon
 6725 format('Extrapolated outer isophote: r,f,sky,eps =',3f9.1,f9.3)
      f0(n+1) = flog
      eps(n+1) = epsilon

      k0last = 1
      incr = .true.
      neval = 0
      do 10 iy = 1,ny
         y = iy - 0.5
C         IF(MOD(IY,50).EQ.0) WRITE(6,'(''+'',i5)') IY
         IF(MOD(IY,10).EQ.0) then
            call tellme('   =*=*= Row',iy,'modelled =*=*=')
         end if
         do 11 ix = 1,nx
            x = ix - 0.5
* First find a pair of bracketing ellipses
            k0 = k0last
            if(incr) k0 = k0last + 1

            xp = +(x-x0(k0))*ca(k0) + (y-y0(k0))*sa(k0)
            yp = -(x-x0(k0))*sa(k0) + (y-y0(k0))*ca(k0)
            rho0 = xp*xp + yp*yp/(eps(k0)*eps(k0))
            if(rho0.lt.r(k0)*r(k0)) then
               k1 = k0 - 1
            else
               k1 = k0 + 1
            end if
            if(k1.lt.0 .or. k1.gt.n+1) then
               write(6,*) 'WHOA THERE.  Pixel outside outer ellipse.'
               write(6,*) 'Try this again'
               rmajor = 1.05*rmajor
               if(counter_666.lt.30) then
                  counter_666 = counter_666 + 1
                  goto 666
               else
                  write(6,*) 'ERROR No convergence after 30 iter'
                  return
               endif
            end if
            xp = +(x-x0(k1))*ca(k1) + (y-y0(k1))*sa(k1)
            yp = -(x-x0(k1))*sa(k1) + (y-y0(k1))*ca(k1)
            rho1 = xp*xp + yp*yp/(eps(k1)*eps(k1))
            if(k0.gt.k1) then
               tmp = rho0
               rho0 = rho1
               rho1 = tmp
               k0 = k1
               k1 = k0 + 1
            end if
* Loop until we are bracketed by a pair of isophotes
 20         continue
            inside = rho0.lt.r(k0)*r(k0)
            outside = rho1.gt.r(k1)*r(k1)
            if(inside.or.outside) then
               k = k0 - 1
               if(outside) k = k1 + 1
               if(k.lt.0 .or. k.gt.n+1) then
                  write(6,*) 'WHOA THERE.  Pixel outside outer ellipse.'
                  write(6,*) 'Try this again'
                  rmajor = 1.05*rmajor
                  if(counter_666.lt.30) then
                     counter_666 = counter_666 + 1
                     goto 666
                  else 
                     write(6,*) 'ERROR No convergence after 30 iter'
                     return
                  endif
               end if
               xp = +(x-x0(k))*ca(k) + (y-y0(k))*sa(k)
               yp = -(x-x0(k))*sa(k) + (y-y0(k))*ca(k)
               rho = xp*xp + yp*yp/(eps(k)*eps(k))
               if(outside) then
                  k0 = k1
                  rho0 = rho1
                  k1 = k
                  rho1 = rho
               else
                  k1 = k0
                  rho1 = rho0
                  k0 = k
                  rho0 = rho
               end if
               goto 20
            end if

* Do a linear interpolation between the two ellipses
* Ideally what we want is the sequence of ellipses with linearly varying
* radius, center, PA, ellipticity, etc, but that is too expensive to compute.
* This is tricky, because the "radius" rho of the point will differ according
* to the two ellipses, and we require a continuous change as the points cross
* bounding ellipses. Assuming that the rho's will not differ much and will
* come close to r(i)^2 as the point approaches one ellipse or the other, let
* us adopt the nearer ellipse's idea of the fraction when we are closer 
* than "1/3" of the distance between the ellipses.
            x0z = x0(k0)
            x1z = x0(k1)
            y0z = y0(k0)
            y1z = y0(k1)
            thz = th(k0)
            dtz = dth(k1)
            ez0 = eps(k0)
            ez1 = eps(k1)
            r0z = rq(k0)
            r1z = rq(k1)
            xpt = x
            ypt = y
            rq0 = sqrt(sqrt(sqrt(rho0)))
            rq1 = sqrt(sqrt(sqrt(rho1)))
            frac = zbrent(elliterp,0.,1.,rq0-r0z,rq1-r1z,1e-4)

C            rq0 = sqrt(sqrt(sqrt(rho0)))
C            rq1 = sqrt(sqrt(sqrt(rho1)))
C            frac0 = (rq0-rq(k0))/(rq(k1)-rq(k0))
C            frac1 = 1 - (rq(k1)-rq1)/(rq(k1)-rq(k0))
C            ave = 0.5*(frac0+frac1)
C            if(ave.gt.2*third) then
C               frac = frac1
C            else if(ave.lt.third) then
C               frac = frac0
C            else
C               frac = frac0 + 3*(frac1-frac0)*(ave-third)
C            end if

* Improve the estimate of frac by iterating
C            fraclast = ave
C            niter = 0
C            do 30 i = 1,maxiter
C               niter = niter + 1
C               x0mid = x0(k0) + frac*(x0(k1)-x0(k0))
C               y0mid = y0(k0) + frac*(y0(k1)-y0(k0))
C               camid = cos(th(k0) + frac*dth(k1))
C               samid = sin(th(k0) + frac*dth(k1))
C               epsmid = eps(k0) + frac*(eps(k1)-eps(k0))
C               xp = +(x-x0mid)*camid + (y-y0mid)*samid
C               yp = -(x-x0mid)*samid + (y-y0mid)*camid
C               rho = xp*xp + yp*yp/(epsmid*epsmid)
C               rmid = sqrt(rho)
C               rqmid = sqrt(sqrt(rmid))
C               fraclast = frac
C               frac = (rqmid-rq(k0))/(rq(k1)-rq(k0))
C               if(abs(frac-fraclast).lt.0.01) goto 31
C 30         continue
C 31         continue
C
C            IF(NITER.GT.3.AND.ITEST.EQ.1) THEN
C               WRITE(6,4526) IX, IY, NITER, FRAC, AVE
C 4526          FORMAT(' (',I4,',',I4,'):',I3,' iterations needed to get'
C     $              ' to',F7.4,' from',F7.4)
C            END IF


* Fill in the data point as a linear combination of ellipse k0 and k1
            arg = f0(k0) + frac*(f0(k1)-f0(k0))
            if(abs(arg).lt.85) then
               data(ix,iy) = exp(arg) + sky
            else
               write(6,4738) ix, iy, arg
 4738          format('Pixel at',2i5,' at exp ',1pg12.2,' set to 0')
               data(ix,iy) = 0
            end if

* If requested, correct the data by the cos3x and cos4x terms
            if(icos4.ne.0.or.icos3.ne.0) then
               cx = xp / rmid
               sx = yp / epsmid / rmid
               c2x = cx*cx - sx*sx
               s2x = 2*cx*sx
               c4x = c2x*c2x - s2x*s2x
               s4x = 2*c2x*s2x
               if(icos3.gt.0) then
                  c3x = c2x*cx - s2x*sx
                  s3x = c2x*sx + s2x*cx
               else
                  c3x = c4x*c2x - s4x*s2x
                  s3x = c4x*s2x + s4x*c2x
               end if
               corr = 0
               if(iabs(icos3).eq.1) then
                  corr = corr + c3med*c3x + s3med*s3x
               else if(iabs(icos3).eq.2) then
                  c3mid = c3(k0) + frac*(c3(k1)-c3(k0))
                  s3mid = s3(k0) + frac*(s3(k1)-s3(k0))
                  corr = corr + c3mid*c3x + s3mid*s3x
               end if
               if(icos4.eq.1) then
                  corr = corr + c4med*c4x + s4med*s4x
               else if(icos4.eq.2) then
                  c4mid = c4(k0) + frac*(c4(k1)-c4(k0))
                  s4mid = s4(k0) + frac*(s4(k1)-s4(k0))
                  corr = corr + c4mid*c4x + s4mid*s4x
               end if
               data(ix,iy) = data(ix,iy)*(1+corr)
            end if

* Set up suggested k0 for the next point
            incr = k0.ge.k0last
            k0last = k0
 11      continue
 10   continue

      write(6,*) neval, ' function evaluations,', 
     $     float(neval)/(float(nx)*float(ny)), ' per point'

      return
      end

      function elliterp(frac)
      common /ellizero/ x0z,x1z,y0z,y1z,thz,dtz,ez0,ez1,r0z,r1z,
     $     xpt,ypt,x0mid,y0mid,camid,samid,epsmid,xp,yp,rmid, neval
      x0mid = x0z + frac*(x1z-x0z)
      y0mid = y0z + frac*(y1z-y0z)
      camid = cos(thz + frac*dtz)
      samid = sin(thz + frac*dtz)
      epsmid = ez0 + frac*(ez1-ez0)
      xp = +(xpt-x0mid)*camid + (ypt-y0mid)*samid
      yp = -(xpt-x0mid)*samid + (ypt-y0mid)*camid
      rho = xp*xp + yp*yp/(epsmid*epsmid)
      rmid = sqrt(rho)
      rqmid = sqrt(sqrt(rmid))
      rqfrac = r0z + frac*(r1z-r0z)
      elliterp = rqmid - rqfrac
      neval = neval + 1
      return
      end
