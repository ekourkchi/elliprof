      SUBROUTINE VARIABLE(VAR, F, SET)
      
C     Routine to set and read variables
      
C     This routine is used to set up or read scalar values associated
C     with an alphanumeric variable name.  These variable names are then
C     accessable from VISTA for use by any commands requiring input
C     or output scalar values.
      
C     Variable names are stored sequentially in the array VARIB
C     as they are defined.  Their values are stored in the corresponding
C     location in VALUE.
      
C     'VAR' is a character*8 variable name
C     'F'   is a DOUBLE PRECISION floating constant to be set or returned
C     'SET' is '.TRUE.' to set variable to 'F'
C     is '.FALSE.' to read variable into 'F'
      
C     Author: Tod R. Lauer            11/3/82
      
* FIXME: this is fragile.  Soft link created by Makefile?
      INCLUDE 'mongo.par'
      INCLUDE 'vistalink.inc'   ! Error communication with VISTA

      real*8 F, value(MAXPRO)
      character*8 varib(MAXPRO), var
      LOGICAL SET
      common /varinameval/ varib, value
      
      DATA VARIB /MAXPRO*' '/

* First check to see whether this is a mongo variable reference
C NB: \\ no worky with gfortran.  Use instead char(92) = \
C      if(var(1:1) .eq. '\\') then
      if(var(1:1) .eq. char(92)) then
         read(var(2:), *, err=666) id
         if(id .ge. 0 .and. id .lt. maxuser) then
            if(set) then
               uservar(id+1) = f
            else
               f = uservar(id+1)
            end if
         end if
         return
      end if
 666  continue

C     Enter lookup loop and try to find 'VAR'.  If found, update variable
C     if SET is true, otherwise, read its value.
      DO 2757 II=1,maxpro
         I = II
         IF (VARIB(I) .EQ. ' ') GO TO 50
         IF (VAR .EQ. VARIB(I)) THEN
            IF (SET) THEN
               VALUE(I)        =F
            ELSE
               F       =VALUE(I)
            END IF
            RETURN
            
         END IF
         
         IF (I .GE. maxpro) THEN
            IF (SET) THEN
               PRINT *,'No more room for variables...'
            ELSE
               PRINT 100, VAR
            END IF
            
            XERR    =.TRUE.
            RETURN
            
         END IF
         
 2757 CONTINUE
      
C     Variable not found.  Define new one if set
C     Return error if not set
      
 50   IF (SET) THEN
         VARIB(I)        =VAR
         VALUE(I)        =F
         
      ELSE
         PRINT 100, VAR
 100     FORMAT (1X,'Variable "',A,'" not found...')
         XERR    =.TRUE.
         
      END IF
      
      RETURN
      END

      subroutine typevars
* FIXME: this is fragile.  Soft link created by Makefile?
      INCLUDE 'mongo.par'

C Just print all the active variables
      include 'vistalink.inc'   ! Error communication with VISTA


      real*8 value(MAXPRO)
      character*8 varib(MAXPRO)
      common /varinameval/ varib, value
      
      do i = 1,maxpro
         if(varib(i) .eq. ' ') return
         print *, varib(i),'=', value(i)
      end do
      
      return
      end
