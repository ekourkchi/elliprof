C     ----------------------------------------------------------------
C     Normalization of the double backend.  ELLIPROFD works on the
C     prepared image multiplied by 2**(-KNORM), an exact power of two
C     chosen by the driver (src/shim/double/prep_d.f NORMEXPD); its
C     intensities are converted back by 2**KNORM.  Intensity keywords
C     (SKY=) and the fallback I0 are converted to these internal units.
C     ----------------------------------------------------------------
        INTEGER KNORM
        COMMON /NORMD/ KNORM
