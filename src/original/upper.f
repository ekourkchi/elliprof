        INTEGER FUNCTION UPPER(CSTRING)

C***    This function converts lower case alphabetics in cstring to
C       upper case and determines the length of the character string
C       in cstring.

C       Author: Richard J. Stover

        CHARACTER*(*) CSTRING
        UPPER   =LEN(CSTRING)
        IF (UPPER.EQ.0) RETURN

C       Look for last non-blank character

        DO 2757 J=UPPER,1,-1
           k = j
           IF (CSTRING(k:k).NE.' ') GOTO 60
 2757   CONTINUE

        k = 0
60      UPPER = k

        IF (UPPER.EQ.0) RETURN

C       Look for lower case letters and convert them to upper case.
C      However, if a '%' is present, then just return.
C      This is a Unix patch to avoid affecting case sensitive
C      Unix commands.

      IF (CSTRING(1:1) .EQ. '%') RETURN
        NTRANS  =ICHAR('A')-ICHAR('a')
        DO 2758 I=1,UPPER
              IF((CSTRING(I:I).GE.'a').AND.(CSTRING(I:I).LE.'z'))THEN
                  CSTRING(I:I)    =CHAR(ICHAR(CSTRING(I:I))+NTRANS)
                END IF
2758        CONTINUE

        RETURN
        END
