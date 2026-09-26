C     Replacements for routines ELLIPROF calls that belonged to the
C     original interactive environment (terminal input, image display).
C     The routine names are fixed by the unchanged elliprof.f.

C     INVISTA: terminal input.  elliprof never reads the terminal: this
C     always reports end of input (0).  ELLIPROF only asks for input
C     with EDIT or TV, which the driver refuses.
      FUNCTION INVISTA(LINE)
      CHARACTER*(*) LINE
      LINE = ' '
      INVISTA = 0
      RETURN
      END

C     MARK: cursor position from the image display.  There
C     is no display, so stop rather than hand back a made-up position.
C     ELLIPROF only calls it with TV when X0/Y0 or R0/R1/NR are missing.
      SUBROUTINE MARK(IROW, ICOL, KEY)
      INTEGER IROW, ICOL
      CHARACTER*(*) KEY
      WRITE (0,*) 'elliprof: TV cursor input is not available;',
     $     ' give X0= Y0= R0= R1= NR= instead'
      CALL EXIT(2)
      END

C     TVCROSS, TVCIRC: overlays on the TV display (tvgraph.f).  No-ops.
      SUBROUTINE TVCROSS(ROW, COL)
      RETURN
      END

      SUBROUTINE TVCIRC(ROW, COL, RAD, PHIN, ECC)
      RETURN
      END

C     TELLME: progress line on stderr, as ccode/tellme.c prints it
C     ("%s %4d %s\r").  ELLIPROF calls it only for "Row N modelled"
C     while building a model image; printed only with --verbose.
      SUBROUTINE TELLME(S1, K, S2)
      CHARACTER*(*) S1, S2
      INTEGER K
      LOGICAL SHVERB
      COMMON /SHIMOPT/ SHVERB
      IF (.NOT. SHVERB) RETURN
      WRITE (0,'(A,1X,I4,1X,A,A)',ADVANCE='NO')
     $     S1(1:LEN_TRIM(S1)), K, S2(1:LEN_TRIM(S2)), CHAR(13)
      FLUSH (0)
      RETURN
      END
