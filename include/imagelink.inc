C       ***     IMAGE PARAMETERS, ADDRESSES, AND CONTROLS       ***

C       This include file contains common blocks holding image
C       parameters, labels, and virtual addresses.

C       The MAXIM parameter controls the maximum number of images that
C       can be handled by VISTA.

        PARAMETER (MAXIM=32)

C       The MAXR and MAXC parameters give the maximum number of columns
C       and rows in a CCD image.

        PARAMETER (MAXR=80000, MAXC=80000)
        PARAMETER (MAXFFT=16384)

C       Each image has a list of parameters specifying such things
C       as its size, conditions of observation, reduction history,
C       identifications, and other information deemed important.
C       The list for each image is held in the array HEADBUF.
C       The HEADBUF for each image is divided into a set of 72 'cards',
C       each of which is 80 columns long.  Each parameter is located
C       on a separate card, identified by a keyword at the start of the
C       card.

        CHARACTER*81840 HEADBUF(MAXIM)
        COMMON /IMGOBJ/ HEADBUF

C       VISTA images are arrays of 2-D floating-point numbers.  The
C       size of the array in each dimension, origin in each dimension,
C       and compression factor in each dimension, are extracted from
C       HEADBUF and held in the integer array ICOORD for convenience.
C       The locations of the various parameters in ICOORD are defined
C       by the following parameters.

        PARAMETER       (NNROW = 1)
        PARAMETER       (NNCOL = 2)
        PARAMETER       (IISR  = 3)
        PARAMETER       (IISC  = 4)
        PARAMETER       (IICMPR= 5)
        PARAMETER       (IICMPC= 6)

        DIMENSION ICOORD(6,MAXIM), ICORNEW(6)
        COMMON /IMGH/ ICOORD, ICORNEW

C       Each image connected with VISTA is assigned an integer image number
C       which is greater than 0 and less than or equal to MAXIM.  An array
C       of logical variables and addresses define the current state of each
C       image number.

C       Variable:       BUFF(IM)        Set .TRUE. if the image number 'IM'
C                                       is connected.
C                       IMCREA          New image buffer number

        LOGICAL BUFF(MAXIM)
        COMMON /IMG/ BUFF, IMCREA

C       Parameters can be passed to subroutines by use of the IMGPIPE common.
C       The common holds the variables needed to specify the condition and
C       origin of the image data array for a maximum of two images, numbered
C       'IM' and 'JM'.

C       Variable:       ISR             Image starting row >=0
C                       ISC             Image starting column >=0
C                       IRBX            Row compression factor >=1
C                       IRCX            Column compression factor >=1

        COMMON /IMGPIPE/ ISR, ISC, IRBX, ICBX, IM, JSR, JSC, JRBX,
     $                   JCBX, JM

C       Author: Tod R. Lauer    11/23/82
