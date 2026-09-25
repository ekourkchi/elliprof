        SUBROUTINE OPERATEd(EQUA,LS,Fdble,LASTOP,IOP)

C       Routine to parse algebraic statements

C       This routine searches for a variable value in
C       the equation characer string 'EQUA', starting at
C       character 'LS'.  The variable's value is returned
C       in 'F', and the next arithmatic operation following
C       it returned in 'IOP'.  This routine is called by routine
C       VALUE, which actually does the operation.

C       CODE:   IOP=0   No operation, end of 'EQUA' found
C               IOP=1   Perform addition next
C               IOP=2   Perform subtraction next
C               IOP=3   Perform multiplication next
C               IOP=4   Perform division next
C               IOP=5   Raise to power next

C 011003 (JT) $OP means do the unary operation OP=LOG,DEX,LN,EXP,SQRT
C               IOP=6   logarithm
C               IOP=7   dex
C               IOP=8   natural log
C               IOP=9   exp
C               IOP=10  sqrt
C               IOP=11  nint
C               IOP=12  int
C               IOP=13  abs
C               IOP=14  cos
C               IOP=15  sin
C               IOP=16  tan
C               IOP=17  acos
C               IOP=18  asin
C               IOP=19  atan
C NOTE: adding or changing requires updating info in varset.f

C       Author: Tod R. Lauer    11/29/82


        INCLUDE 'vistalink.inc'                 ! Error communication
        INTEGER UPPER
        CHARACTER*80 EQUA, LOOKUP
        CHARACTER*80 VAR
        parameter (maxop=6)
        CHARACTER*1 OP(maxop)
        real*8 Fdble
        LOGICAL NEG, ERR
        DATA OP /'+','-','*','/','^','$'/

* Are we past the end?
        if(ls.gt.80) then
           iop = -1
           return
        end if

* Update the previous IOP
        lastop = iop

C       Check to see if variable is negative
        NEG     =.FALSE.                        ! If the first character is a
        IF (EQUA(LS:LS) .EQ. '-') THEN          ! a minus sign, set NEG flag
                NEG     =.NOT.NEG                 ! and increment pointer.
                LS      =LS+1
        END IF

        IF (EQUA(LS:LS) .EQ. '-') THEN          ! But -- is +
                NEG     =.NOT.NEG
                LS      =LS+1
        END IF

        LOP     =81                     ! Pointer to operation character
        IOP     =0                      ! Next operation

C       Search for any operation characters.  Search from the pointer onward.
C       Stop at the nearest one.
        DO 2757 I=1, maxop
                L       =INDEX(EQUA(LS:80),OP(I))
                IF (L .NE. 0 .AND. L .LT. LOP-LS+1) THEN
                        LOP     =L+LS-1
                        IOP     =I
                END IF
2757        CONTINUE

C       If a '+' or '-' has been detected, check to see if it might be
C       part of an exponential specifier.  Look for the next operator
C       and pass the string to dissect to see if it can be interpretted
C       as a floating number.

        IF (IOP .EQ. 1 .OR. IOP .EQ. 2) THEN            ! '+' or '-' found
                JOP     =0
                JS      =MIN0(LOP+1,80)
                JE      =MIN0(LOP+3,80)
                LNOP    =JE+1
                DO 2758 I=1, maxop
                        L       =INDEX(EQUA(JS:JE),OP(I))
                        IF (L .NE. 0 .AND. L .LT. LNOP-JS+1) THEN
                                LNOP    =L+JS-1
                                JOP     =I
                        END IF

2758                CONTINUE

                IF (JOP .EQ. 0) THEN                    ! Check for ' '
                        JE      =UPPER(EQUA(LS:LNOP-1))+LS-1
                ELSE
                        JE      =LNOP-1
                END IF

                LOOKUP  =EQUA(LS:JE)
                CALL DISSECT(LOOKUP,1,.TRUE.,ITY,N,F,VAR,NCH,ERR)
                IF (ITY .EQ. 2) THEN                    ! String is a number
                        IOP     =JOP
                        LOP     =LNOP
                END IF
        END IF


C       Pack in variable characters.  LOOKUP is a string extracted from the
C       expression, which should either be a varible name or a number.

        LE      =LOP-1
        IF (LE .LT. LS) THEN                    ! No LOOKUP string
                PRINT *,'Illegal syntax: ', EQUA(LS:LS+2)
                XERR    =.TRUE.
                RETURN
        END IF

        LOOKUP  =EQUA(LS:LE)

* Check to see whether the previous IOP was '$' and we have a legal
* unary operation
        if(lastop.eq.6) then
           ll = upper(lookup)
           lastop = -1
           if(ll.eq.3 .and. lookup(:ll) .eq. 'LOG')  lastop = 6
           if(ll.eq.3 .and. lookup(:ll) .eq. 'DEX')  lastop = 7
           if(ll.eq.2 .and. lookup(:ll) .eq. 'LN')   lastop = 8
           if(ll.eq.3 .and. lookup(:ll) .eq. 'EXP')  lastop = 9
           if(ll.eq.4 .and. lookup(:ll) .eq. 'SQRT') lastop = 10
           if(ll.eq.4 .and. lookup(:ll) .eq. 'NINT') lastop = 11
           if(ll.eq.3 .and. lookup(:ll) .eq. 'INT')  lastop = 12
           if(ll.eq.3 .and. lookup(:ll) .eq. 'ABS')  lastop = 13
           if(ll.eq.3 .and. lookup(:ll) .eq. 'COS')  lastop = 14
           if(ll.eq.3 .and. lookup(:ll) .eq. 'SIN')  lastop = 15
           if(ll.eq.3 .and. lookup(:ll) .eq. 'TAN')  lastop = 16
           if(ll.eq.4 .and. lookup(:ll) .eq. 'ACOS') lastop = 17
           if(ll.eq.4 .and. lookup(:ll) .eq. 'ASIN') lastop = 18
           if(ll.eq.4 .and. lookup(:ll) .eq. 'ATAN') lastop = 19
           if(lastop.eq.-1) then
              print *, 'undefined unary operation "', lookup(:ll),'"'
              xerr    =.true.
           end if
           goto 100
        end if

C       Interpret variable value LOOKUP.  If DISSECT declares it to be a
C       character string, then LOOKUP must contain the name of a variable.
C       Call VARIABLE to find its value.  Otherwise, LOOKUP is a number,
C       and DISSECT will return its floating numerical value in F.

        CALL DISSECTd(LOOKUP,1,.TRUE.,ITY,N,Fdble,VAR,NCH,ERR)
        IF (ERR) THEN
                PRINT *,'Undefined parameter'
                XERR    =.TRUE.
                RETURN
        END IF

        IF (ITY .GE. 3) THEN                    ! LOOKUP is a variable
                CALL VARIABLE(VAR, Fdble, .FALSE.)
                IF (XERR) RETURN
        END IF

 100    IF (NEG) Fdble = -Fdble     ! Negate value if flag set
        LS      =LE+2           ! Update pointer to look for

        RETURN                  ! next operation.
        END
