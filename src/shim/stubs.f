C     Replacements for the MONSTA routines ELLIPROF calls that need
C     the Mongo terminal layer or the X11 image display.

C     INVISTA: one line of terminal input (sysdepG77.f uses Mongo's
C     readline input).  Returns 1 for text, 0 at end of file.
      FUNCTION INVISTA(LINE)
      CHARACTER*(*) LINE
      READ (5,'(A)',END=10,ERR=10) LINE
      INVISTA = 1
      RETURN
 10   LINE = ' '
      INVISTA = 0
      RETURN
      END

C     MARK: cursor position from the TV display (zimvista.c).  There
C     is no display, so stop rather than hand back a made-up position.
C     ELLIPROF only calls it with TV when X0/Y0 or R0/R1/NR are missing.
      SUBROUTINE MARK(IROW, ICOL, KEY)
      INTEGER IROW, ICOL
      CHARACTER*(*) KEY
      WRITE (0,*) 'elliprof: TV cursor input is not available;',
     $     ' give X0= Y0= R0= R1= NR= instead'
      STOP 2
      END

C     TVCROSS, TVCIRC: overlays on the TV display (tvgraph.f).  No-ops.
      SUBROUTINE TVCROSS(ROW, COL)
      RETURN
      END

      SUBROUTINE TVCIRC(ROW, COL, RAD, PHIN, ECC)
      RETURN
      END

C     TELLME: progress line on stderr, as ccode/tellme.c prints it
C     ("%s %4d %s\r").
      SUBROUTINE TELLME(S1, K, S2)
      CHARACTER*(*) S1, S2
      INTEGER K
      WRITE (0,'(A,1X,I4,1X,A,A)',ADVANCE='NO')
     $     S1(1:LEN_TRIM(S1)), K, S2(1:LEN_TRIM(S2)), CHAR(13)
      FLUSH (0)
      RETURN
      END
