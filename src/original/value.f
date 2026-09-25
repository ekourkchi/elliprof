      SUBROUTINE VALUEd(EQUA, ACCUM)

C     This routine interprets an algebraic string

C     This routine is used by other routines to calculate the value
C     of an algebraic expression which may include variables and
C     constants.  The desired operation is simply done on a left to
C     right basis, scanning through the input expression.  There is
C     no hierarchy of operation.  Parentheses are not allowed.

C     INPUT:  EQUA    A character string containing the expression

C     OUTPUT: ACCUM   The floating numerical interpretation of EQUA

C     Author: Tod R. Lauer    11/29/82

      INCLUDE 'vistalink.inc'   ! Communication with VISTA
      CHARACTER*(*) EQUA
* 120708 JT: change to double precision!
      real*8 accum, f

C     Interpret algebraic string and perform artihmatic operations.
C     The subroutine OPERATE gets the first value of the accumulator
C     and then checks to see if an operation is to be performed on it.
C     If so, it gets the next value 'F' which will operate on the
C     accumulator, and checks for yet another operation to be performed
C     on the result.  This looping continues until no more operations
C     are found.

      LS      =1                ! Pointer to character in EQUA
      iop = 0
      CALL OPERATEd(EQUA,LS,F,LASTOP,IOP) ! Get first operation and value

      IF (XERR) RETURN
      ACCUM   =F                ! Initialize accumulator
 50   IF (IOP .EQ. 0) RETURN    ! Return if no more operations
      CALL OPERATEd(EQUA,LS,F,LASTOP,IOP) ! Get the value needed for the LASTOP
      if(iop.eq.-1) return      ! Off the end of string
      IF (XERR) RETURN          ! operation, and get the next operation

C     Branch to operation

      GO TO (71,72,73,74,75,76,77,78,79,80,81,82,83,84,85,86,87,88,89) 
     $     ,LASTOP

 71   ACCUM   =ACCUM+F          ! Add
      GO TO 50

 72   ACCUM   =ACCUM-F          ! Subtract
      GO TO 50

 73   ACCUM   =ACCUM*F          ! Multiply
      GO TO 50

 74   IF (F .EQ. 0.0) THEN      !Divide
         PRINT *,'Divide by zero requested'
         XERR    =.TRUE.
         RETURN

      ELSE
         ACCUM   =ACCUM/F

      END IF
      GO TO 50

 75   IF (ACCUM .LT. 0.0) THEN  ! Raise to power
         PRINT *,'Can''t raise a negative number to a power'
         XERR    =.TRUE.
      ELSE IF (ACCUM .GT. 0.0) THEN
         IF (daBS(F*dLOG10(ACCUM)) .LE. 255.0) THEN
            ACCUM   =ACCUM**F
         ELSE
            PRINT *,'Floating point overflow...'
            XERR    =.TRUE.
         END IF
      END IF

      GO TO 50                  ! Get next operation

 76   if (accum .le. 0.0) then  ! logarithm
         print *,'Can''t take log of a nonpositive number'
         xerr    =.true.
      else
         accum = dlog10(accum)
      end if
      go to 50                  ! Get next operation

 77   if (accum .lt. -255) then  ! dex
         accum = 0
      else if (accum .gt. 255) then
         print *,'Floating point overflow...'
         xerr    =.true.
      else
         accum = 10.0**accum
      end if
      go to 50                  ! Get next operation

 78   if (accum .le. 0.0) then  ! ln
         print *,'Can''t take log of a nonpositive number'
         xerr    =.true.
      else
         accum = dlog(accum)
      end if
      go to 50                  ! Get next operation

 79   if (accum .lt. -500) then  ! exp
         accum = 0
      else if (accum .gt. 500) then
         print *,'Floating point overflow...'
         xerr    =.true.
      else
         accum = dexp(accum)
      end if
      go to 50                  ! Get next operation

 80   if (accum .lt. 0.0) then  ! sqrt
         print *,'Can''t sqrt a negative number'
         xerr    =.true.
      else
         accum = dsqrt(accum)
      end if
      go to 50                  ! Get next operation

 81   if (dabs(accum) .gt. 2.0**31) then ! nint
         print *,'Number too large to fix'
         xerr    =.true.
      else
         accum = nint(accum)
      end if
      go to 50                  ! Get next operation

 82   if (dabs(accum) .gt. 2.0**31) then ! int
         print *,'Number too large to fix'
         xerr    =.true.
      else
         accum = int(accum)
      end if
      go to 50                  ! Get next operation

 83   accum = dabs(accum)      ! abs
      go to 50                  ! Get next operation

 84   accum = dcos(accum)      ! cos
      go to 50                  ! Get next operation

 85   accum = dsin(accum)      ! sin
      go to 50                  ! Get next operation

 86   accum = dtan(accum)      ! tan
      go to 50                  ! Get next operation

 87   if (dabs(accum) .gt. 1d0) then ! acos
         print *,'Argument too large for acos', accum
         xerr    =.true.
      else
         accum = dacos(accum)
      end if
      go to 50                  ! Get next operation

 88   if (dabs(accum) .gt. 1d0) then ! asin
         print *,'Argument too large for asin', accum
         xerr    =.true.
      else
         accum = dasin(accum)
      end if
      go to 50                  ! Get next operation

 89   accum = datan(accum)      ! atan
      go to 50                  ! Get next operation


      END
