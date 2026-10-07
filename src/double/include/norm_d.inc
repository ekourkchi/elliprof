C     ----------------------------------------------------------------
C     Normalization of the double backend.  ELLIPROFD works on the
C     prepared image multiplied by 2**(-KNORM), an exact power of two
C     chosen by the driver (src/shim/double/prep_d.f NORMEXPD); its
C     intensities are converted back by 2**KNORM.  Intensity keywords
C     (SKY=) and the fallback I0 are converted to these internal units.
C     ----------------------------------------------------------------
C     Model counters, set by SYNTHESIZED in physical units (R6):
C     NUNDER pixels whose model underflowed to zero, NSUBN pixels whose
C     model is subnormal (nonzero, reduced precision), NOVERM pixels
C     whose finite model is beyond the double range (an error).
C     MODPHY is true once SYNTHESIZED has left the whole model in
C     physical units (the driver then does not rescale it).
        INTEGER KNORM, NUNDER, NSUBN, NOVERM
        LOGICAL MODPHY
        COMMON /NORMD/ KNORM, NUNDER, NSUBN, NOVERM, MODPHY
