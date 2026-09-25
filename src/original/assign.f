      SUBROUTINE ASSIGN(EQUALITY, ACCUM, PARM)
      CHARACTER*(*) EQUALITY, PARM
      real*8 daccum
      call ASSIGNspdp(EQUALITY, ACCUM, daccum, PARM)
      return
      end

      SUBROUTINE ASSIGNd(EQUALITY, DACCUM, PARM)
      CHARACTER*(*) EQUALITY, PARM
      real*8 daccum
      call ASSIGNspdp(EQUALITY, ACCUM, daccum, PARM)
      return
      end

      SUBROUTINE ASSIGNspdp(EQUALITY, ACCUM, daccum, PARM)

C       This routine interprets an equality of the form: PARM=F

C       This routine is used by VISTA subroutines to assign a value
C       to an input variable or keyword.

C       INPUT:  EQUALITY        A character string of the form
C                               PARM='number, variable, or combined expression'

C       OUTPUT: PARM            A character string containing the keyword
C               ACCUM           The floating numerical value of the expression
C                               on the right hand side of the equation.

C       Author: Tod R. Lauer    11/29/82

        INCLUDE 'vistalink.inc'         ! Error communication with VISTA
        INTEGER UPPER
        LOGICAL ERR, EQ
        CHARACTER*(*) EQUALITY, PARM
        CHARACTER*256 EQUA
        real*8 daccum

C       Locate and isolate the parameter character string

        EQ      =.TRUE.                 ! Tell DISSECT that '=' is a space
        L       =UPPER(EQUALITY)
        CALL DISSECT(EQUALITY,1,EQ,ITY,N,F,PARM,NCH,ERR)
        IF (ITY .LT. 3 .OR. ERR) THEN
                PRINT 100, EQUALITY(1:L)
100             FORMAT(1X,'Illegal parameter in ',A)
                XERR    =.TRUE.
                RETURN
        END IF

C       Locate the parameter value

        CALL DISSECT(EQUALITY,2,EQ,ITY,N,F,EQUA,NCH,ERR)
        IF (ERR) THEN
                PRINT 101, EQUALITY(1:L)
101             FORMAT (1X,'Missing expression in ',A)
                XERR    =.TRUE.
                RETURN
        END IF

        CALL VALUEd(EQUA, dACCUM)          ! Interpret the parameter value
        accum = sngl(daccum)

        RETURN
        END
