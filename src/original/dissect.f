      SUBROUTINE DISSECT(ISTRNG, IWORD, EQFLAG,
     $     OTYPE, ONUM, FNUM, OSTRNG, NCHAR, OERR)
      CHARACTER*(*) ISTRNG, OSTRNG
      LOGICAL EQFLAG, OERR
      INTEGER OTYPE, ONUM
      real *8 Fdble
      call DISSECTSPDP(ISTRNG,IWORD,EQFLAG,OTYPE,ONUM,FNUM,Fdble,OSTRNG,
     $     NCHAR,OERR)
      return
      end
      
      SUBROUTINE DISSECTd(ISTRNG, IWORD, EQFLAG,
     $     OTYPE, ONUM, Fdble, OSTRNG, NCHAR, OERR)
      CHARACTER*(*) ISTRNG, OSTRNG
      LOGICAL EQFLAG, OERR
      INTEGER OTYPE, ONUM
      real *8 Fdble
      call DISSECTSPDP(ISTRNG, IWORD, EQFLAG,
     $     OTYPE, ONUM, FNUM, Fdble, OSTRNG, NCHAR, OERR)
      return
      end
      
      SUBROUTINE DISSECTSPDP(ISTRNG, IWORD, EQFLAG,
     $     OTYPE, ONUM, FNUM, Fdble, OSTRNG, NCHAR, OERR)
      
C     Parse a line of text for words or numeric values.
      
C     This subroutine extracts individual words from a line
C     of text.  The routine returns the word string if the
C     requested word is located.  Words are separated by spaces,
C     tabs, commas, and = signs (if specified).  Statements within
C     in single quotes or parentheses are considered to be one word.  If the
C     the word can be interpretted as a numerical value, its integer
C     and floating value is returned.  The routine understands all
C     FORTRAN 77 floating point representations.
      
C     Input:  
C
C     ISTRNG  The input text string
C     IWORD   Specifies which word of istrng to extract
C     EQFLAG  Logical variable (.FALSE. if equal sign has special meaning, 
C             .TRUE. if equal sign is to be treated like a space character)
C
C     Output: 
C
C     OERR    Set to .TRUE. if the requested word is not
C             present in istrng.  otherwise oerr is set to .FALSE..
C     NCHAR   Number of characters in the extracted word
C     OSTRNG  The actual word extracted
C     FNUM    The floating point value of the word if the word was a number
C     Fdble   The DP floating point value of the word if the word was a number
C     ONUM    The integer value of the word if the word was a number
C     OTYPE   Tells what type of word was found
C     1 = Integer (no decimal point)
C     2 = Floating point (decimal point or exponent found)
C     3 = Character string (non-numerics found)
      
C     If OTYPE=3 then ONUM and FNUM are set to 0.
C     If OTYPE=2 then ONUM is the integer part of FNUM.
      
C     Words in the input string can be separated by any number
C     of tabs, spaces, or commas.
      
C     Author: Richard J. Stover       3/23/83
      
      CHARACTER*(*) ISTRNG, OSTRNG
      CHARACTER C, TAB, EQ, CS, LASTC
      LOGICAL OERR, SPACE, EQFLAG, QUOTE, PAREN, PAREN2, EXP
      INTEGER OTYPE, ONUM, CVAL
      real*8 Fdble
      
C     Define function to check for space characters and initialize
      
      SPACE(CS,EQ)=(CS.EQ.' ').OR.(CS.EQ.',').OR.(CS.EQ.CHAR(9)).OR.
     #(CS.EQ.EQ)
      
      TAB     ='	'
CCJT

C      OSTRNG(1:LEN(OSTRNG))=' '
      OSTRNG=' '
      ONUM    =0
      FNUM    =0.0
      Fdble   =0d0
      IF (IWORD .LT. 1) THEN    ! Illegal word requested
         OERR    =.TRUE.
         RETURN
      END IF
      
      IF (EQFLAG) THEN          ! An equal sign will be
         EQ      ='='           ! considered to be a space.
      ELSE
         EQ      =' '
      END IF
      
      OERR    =.FALSE.
      QUOTE   =.FALSE.
      PAREN   =.FALSE.
      PAREN2  =.FALSE.
      JCHAR   =0
      LASTC   =' '
      ILEN    =LEN(ISTRNG)
      JWORD   =1                ! Current word pointer
      
C     Look through the input string, skipping over spaces, to find
C     word number IWORD.
      
      DO 100 J=1,ILEN
         C       =ISTRNG(J:J)   ! Current character
         IF (SPACE(C,EQ)) GO TO 50 ! C is a space character
         IF (C.EQ.''''.AND.(.NOT.QUOTE).AND.SPACE(LASTC,EQ)) THEN
            K       =J+1
            QUOTE   =.TRUE.
         ELSE
            K       =J
         END IF
         
C     Check for parenthesis...anything inside of them will not
C     be considered a space character.
         
         IF (C.EQ.')') THEN
            PAREN   =.FALSE.
         END IF
         
         IF (C.EQ.'(') THEN
            PAREN   =.TRUE.
         END IF
         
         IF (JWORD.EQ.IWORD) THEN ! Word has been located.
            JSTART=K            ! Its first character location
            GO TO 200           ! Leave to process word.
         END IF
         
         JCHAR   =1
         GO TO 90
 50      IF (J.EQ.1) GOTO 90
         IF (PAREN) GOTO 90
         IF (QUOTE) THEN
            IF ((ISTRNG(J-1:J-1).EQ.'''').AND.(J.NE.K)) THEN
               QUOTE   =.FALSE.
               JWORD   =JWORD+1
               JCHAR   =0
               GO TO 90
            END IF
            GO TO 90
         END IF
         
         IF (JCHAR.EQ.1) JWORD=JWORD+1
         JCHAR   =0
 90      LASTC   =C
 100  CONTINUE
      
      OERR    =.TRUE.           ! Word number IWORD not found
      RETURN
      
C     Determine where the end of this string is located
      
 200  LASTC   =' '
      DO 2757 J=JSTART+1,ILEN
         JEND    =J-1
         C       =ISTRNG(J:J)
         IF (SPACE(C,EQ).AND.(.NOT.PAREN)) THEN
            IF (QUOTE) THEN
               IF (LASTC.EQ.'''') THEN
                  JEND    =JEND-1
                  GOTO 300
               END IF
            ELSE
               GOTO 300
            END IF
         END IF
         
         IF (C.EQ.')') THEN
            PAREN   =.FALSE.
            PAREN2  =.TRUE.
         END IF
         
         IF (C.EQ.'(') THEN
            PAREN   =.TRUE.
         END IF
         
         LASTC   =C
 2757 CONTINUE
      
      JEND    =ILEN
      
C     Word IWORD has been isolated.  Load it into output.  Go through
C     to determine its type.
      
 300  NCHAR   =JEND-JSTART+1
      if(nchar.gt.len(ostrng)) then
         write(6,*) 'Dissect: OSTRNG is too small for word!!!'
         write(6,711) ISTRNG(JSTART:JEND), nchar, len(ostrng)
 711     format('Input = "',a,'"',i3,' char, param only has length', i3)
         write(6,*) 'Going to truncate, but this may be bad...'
         nchar = len(ostrng)
         ostrng =istrng(jstart:jend)
      else
         OSTRNG(1:NCHAR) =ISTRNG(JSTART:JEND)
      end if
      IF (QUOTE) THEN           ! Word defined to be string
         OTYPE   =3
         RETURN
      END IF
      
      IF (PAREN.OR.PAREN2) THEN ! Word defined to be string
         OTYPE   =3
         RETURN
      END IF
      
      NEG     =0
      
C***  If NCHAR=1 then the word must be a single numeric character to
C     be a number.
      
      IF (NCHAR.EQ.1) THEN
         C       =OSTRNG(1:1)
         IF((C.LT.'0').OR.(C.GT.'9')) THEN ! It is not numeric
            OTYPE   =3
            RETURN
         END IF
      END IF
      
C***  Decode the field character by character.  Stop if a non-numeric
C     character is found; otherwise update numeric values as each character
C     is decoded.
      
      OTYPE   =1
      EXP     =.FALSE.
      NEXP    =0
      ENUM    =0.0
      ESGN    =1.0
      DO 5000 J=1,NCHAR
         C       =OSTRNG(J:J)
         CVAL    =ICHAR(C)-ICHAR('0')
         IF (J.EQ.1) THEN       ! Check for sign specifier at
            IF (C.EQ.'-') THEN  ! the start of the word.
               NEG     =1
               GOTO 5000
            END IF
            IF (C.EQ.'+') GOTO 5000
         END IF
         IF (EXP) GO TO 1001
         IF (OTYPE.EQ.2) GOTO 1000
         
C***  OTYPE=1 means an integer is assumed
         
         IF (C.EQ.'.') THEN
            OTYPE   =2          ! Must be floating
            NPOINT  =1
            GO TO 5000
         END IF
         
         IF ((C.GE.'0').AND.(C.LE.'9')) THEN ! Update numeric values
            ONUM    =10*ONUM+CVAL
            FNUM    =FLOAT(ONUM)
            Fdble = dble(onum)
            GO TO 5000
         ELSE IF (C .EQ. 'E' .OR. C .EQ. 'e') THEN ! Exponent found?
            IF (J .LT. NCHAR) THEN
               OTYPE   =2
               EXP     =.TRUE.
               GO TO 5000
            ELSE
               OYTPE   =3
               ONUM    =0
               FNUM    =0.0
               Fdble   =0d0
               RETURN
            END IF
         ELSE                   ! Otherwise must be character
            OTYPE   =3          ! Zero out values and return
            ONUM    =0
            FNUM    =0.0
            Fdble   =0d0
            RETURN
         END IF
         
C***  OTYPE=2 means floating is assumed
         
 1000    IF ((C.GE.'0').AND.(C.LE.'9')) THEN
            FNUM    =FNUM+FLOAT(CVAL)*10.0**(-NPOINT)
            Fdble = Fdble + dble(CVAL)*10d0**(-NPOINT)
            NPOINT  =NPOINT+1
            GO TO 5000
         ELSE IF (C .EQ. 'E' .OR. C .EQ. 'e') THEN ! Exponent detected
            IF (J .LT. NCHAR) THEN
               OTYPE   =2
               EXP     =.TRUE.
               GO TO 5000
            ELSE
               OYTPE   =3
               ONUM    =0
               FNUM    =0.0
               Fdble = 0d0
               RETURN
            END IF
         ELSE
            OTYPE   =3          ! Must be character
            ONUM    =0
            FNUM    =0.0
            Fdble = 0d0
            RETURN
         END IF
         
C     Build up exponent here
         
 1001    IF (NEXP .EQ. 0) THEN
            NEXP    =1
            IF (C .EQ. '+') THEN ! Load exponential sign
               ESGN    =1.0
               GO TO 5000
            ELSE IF (C .EQ. '-') THEN
               ESGN    =-1.0
               GO TO 5000
            END IF
         END IF
         
         IF ((C.GE.'0').AND.(C.LE.'9').AND. NEXP .LE. 2) THEN
            ENUM    =10.0*ENUM+CVAL
            NEXP    =NEXP+1
            GO TO 5000
         ELSE                   ! Otherwise must be character
            OTYPE   =3          ! Zero out values and return
            ONUM    =0
            FNUM    =0.0
            Fdble = 0d0
            RETURN
         END IF
         
         
 5000 CONTINUE
      
C     Finish exponent if specified
      
      IF (EXP) THEN
         IF (FNUM .NE. 0.0) THEN
            TEST    =ALOG10(FNUM)+ESGN*ENUM
         ELSE
            TEST    =ESGN*ENUM
         END IF
         IF (ABS(TEST) .LE. 38.0 .AND. ENUM .LE. 38.0) THEN
            FNUM    =FNUM*10.0**(ESGN*ENUM)
            IF (ABS(FNUM) .LE. 2.0E9) THEN
               ONUM    =NINT(FNUM)
            ELSE
               ONUM    =0
            END IF
         ELSE
            OTYPE   =3
            FNUM    =0.0
            ONUM    =0
         END IF

         IF (Fdble .NE. 0d0) THEN
            TEST    = sngl(dLOG10(Fdble)+ESGN*ENUM)
         ELSE
            TEST    =ESGN*ENUM
         END IF
         IF (ABS(TEST) .LE. 255.0 .AND. ENUM .LE. 255.0) THEN
            Fdble = Fdble*10.0**(esgn*enum)
            IF (ABS(Fdble) .LE. 2.0d9) THEN
               ONUM    =NINT(Fdble)
            ELSE
               ONUM    =0
            END IF
         ELSE
            OTYPE   =3
            Fdble = 0d0
            ONUM    =0
         END IF
      END IF
      
C***  Check for minus sign flag.
      
      IF (NEG .EQ. 1) THEN
         ONUM    =-ONUM
         FNUM    =-FNUM
         Fdble = -Fdble
      END IF
      
      RETURN
      END

C     Parse a string into tokens and return the lengths (JT:060926)
      subroutine parser(input, maxword, nword, length, word)
C     INPUT = source line
C     MAXWORD = max number of tokens allowed
C     NWORD = number of tokens found
C     LENGTH = array of token lengths
C     WORD = array of tokens
      character*(*) input, word(maxword)
      integer length(maxword)
      logical blank, prev
      data itab /9/

      prev = .true.
      nword = 0
      do 10 i = 1,len(input)
         blank = input(i:i).eq.' ' .or. ichar(input(i:i)).eq.0 .or.
     $        ichar(input(i:i)).eq.itab
         if(.not.blank) then
            if(prev) then
               if(nword.ge.maxword) then
                  write(6,*) 'PARSE: Cannot parse so many words'
                  return
               end if
               nword = nword + 1
               length(nword) = 1
               word(nword) = input(i:i)
            else
               if(length(nword).ge.len(word(nword))) then
                  write(6,*) 'PARSE: Cannot parse such a long word: ', 
     $                 word(nword)
               else
                  length(nword) = length(nword) + 1
                  word(nword)(length(nword):length(nword)) = input(i:i)
               end if
            end if
         end if
         prev = blank
 10   continue
      return
      end
