C       ***     SURFACE PHOTOMETRY PARAMETRS            ***

C       The profile calculations are held in the PRF common block.  The
C       parameters kept for each contour are as follows:

C               1       Contour central row number
C               2       Contour central column number
C               3       Position angle of contour, N at image top
C               4       Eccentricty of contour
C               5       Average surface brightness of contour
C               6       N=4 sine component of contour (average)
C               7       N=4 cosine component
C               8       N=2 sine component
C               9       N=2 cosine component
C              10       N=1 sine component
C              11       N=1 cosine component
C              12       Contour intensity derivative

C       N_PRF           The number of contours
C       PRF_SC          The image scale ''/pixel

        PARAMETER (NPROFILE=250)        
        REAL*4 PARAM_PRF(12,NPROFILE)
        CHARACTER*81840 PRF_HEAD
        COMMON /PRF/ N_PRF, PRF_SC, PARAM_PRF
        COMMON /PRF_NAME/ PRF_HEAD
