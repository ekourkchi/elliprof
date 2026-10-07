C     ----------------------------------------------------------------
C     Double-precision counterpart of include/profile.inc, for the
C     double backend only (src/double, src/shim/double).  Separate
C     COMMON blocks: /PRFD/ and /PRFNMD/ never alias /PRF/ and
C     /PRF_NAME/ of the single backend.  Same layout and meaning as
C     profile.inc, with PARAM_PRF and PRF_SC in DOUBLE PRECISION.
C     N_PRF is declared INTEGER explicitly because the units including
C     this file use IMPLICIT DOUBLE PRECISION (A-H,O-Z).
C     ----------------------------------------------------------------
        PARAMETER (NPROFILE=250)
        INTEGER N_PRF
        DOUBLE PRECISION PRF_SC, PARAM_PRF(12,NPROFILE)
        CHARACTER*81840 PRF_HEAD
        COMMON /PRFD/ PARAM_PRF, PRF_SC, N_PRF
        COMMON /PRFNMD/ PRF_HEAD
