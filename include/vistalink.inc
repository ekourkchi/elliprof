C       ***     VISTA KEYWORDS, PARAMETERS, AND CONTROL         ***

C       This include file controls communication between VISTA and
C       its subroutines.

C       Parameters:     NCON            The maximum length of the VISTA
C                                       integer, constant, and keyword buffers.
C                       MAXPRO          The maximum number of lines in the
C                                       VISTA procedure buffer.

        PARAMETER (NCON=16, MAXPRO=2000)

C       These variables pass constants and keywords to the subroutines.

C       Variable:       CONST   Floating constants buffer
C                       IBUF    Integer constants buffer
C                       WORD    Keywords and alphanumeric buffer (upper case)
C                       COM     Current VISTA command (upper case)
C                       COMMAND Full input command line (upper case)
C                   origWORD    Keywords and alpha buffer (original case)
C                   origCOMMAND Full input command line (original case)
C                   idxword     Index of alpha token in input line (or 0)
C                   idxint      Index of integer token in input line (or 0)
C                   idxfloat    Index of floating token in input line (or 0)
C
C                monsta                0 for mongo, 1 for Vista

        DIMENSION CONST(NCON), IBUF(NCON)
        integer idxfloat(ncon), idxint(ncon), idxword(ncon)
        CHARACTER*289 WORD(NCON), COM, origword(ncon)
        CHARACTER*289 COMMAND, origcommand
        COMMON /VISCON/ idxword, idxint, idxfloat, CONST, IBUF, monsta
        COMMON /VISALPH/ COM, COMMAND, WORD, origcommand, origword

C       These logical variables control subroutine program flow.

C       Variable:       GO      Set by VISTA to start the subroutine
C                       CHECK   Set .FALSE. in subroutines to indicate
C                               an error in input before VISTA sets GO.
C                       XERR    Set .TRUE. in subroutines when an error
C                               occurs during execution.  If the error
C                               is severe enough, the routine should
C                               imediately return to VISTA.
C                       NOGO    Set .TRUE. when Ctrl-C is entered from
C                               the keyboard.  Subroutines can check
C                               this at any desired point, and return
C                               if set.
C                        XEOF   Set .TRUE. if an END-OF-FILE is
C                               detected during the reading of an
C                               external data file.

        LOGICAL GO, CHECK, XERR, NOGO, XEOF
        COMMON /CON/ GO, CHECK, XERR, NOGO, XEOF

C       Author: Tod R. Lauer            11/5/82

* The unit number to use in connecting to the stdout
      integer ttylun, redirlun
      common /ttycom/ ttylun, redirlun
