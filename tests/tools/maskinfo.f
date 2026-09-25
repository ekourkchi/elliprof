C     Decode a mask with the standalone reader (src/shim/maskio.f) and
C     summarise it: header, value counts, masked fraction, and
C     optionally the values around one pixel.
C
C     Usage: maskinfo mask [col row [half]]
C        (col,row) are 1-based pixel indices; the box is 2*half+1 wide.

      PROGRAM MASKINFO
      REAL, ALLOCATABLE :: M(:,:)
      CHARACTER*1024 FNAME, ARG
      CHARACTER*200 LINE
      INTEGER MBITPIX, MCOL, MROW, MSC, MSR, IOFF, IERR
      INTEGER NARGS, IC, IR, IH, I, J, N0, N1, NX, NB0

      NARGS = COMMAND_ARGUMENT_COUNT()
      IF (NARGS .LT. 1) THEN
         WRITE (0,*) 'usage: maskinfo mask [col row [half]]'
         STOP 1
      END IF
      CALL GET_COMMAND_ARGUMENT(1, FNAME)
      IC = 0
      IR = 0
      IH = 10
      IF (NARGS .GE. 3) THEN
         CALL GET_COMMAND_ARGUMENT(2, ARG)
         READ (ARG,*) IC
         CALL GET_COMMAND_ARGUMENT(3, ARG)
         READ (ARG,*) IR
      END IF
      IF (NARGS .GE. 4) THEN
         CALL GET_COMMAND_ARGUMENT(4, ARG)
         READ (ARG,*) IH
      END IF

      CALL MASKHEAD(FNAME, MBITPIX, MCOL, MROW, MSC, MSR, IOFF, IERR)
      IF (IERR .NE. 0) STOP 1
      ALLOCATE (M(MCOL,MROW))
      CALL MASKREAD(FNAME, MBITPIX, IOFF, MCOL, MROW, M, IERR)
      IF (IERR .NE. 0) STOP 1

      N0 = 0
      N1 = 0
      NX = 0
      DO 10 J = 1, MROW
         DO 11 I = 1, MCOL
            IF (M(I,J) .EQ. 0.0) THEN
               N0 = N0 + 1
            ELSE IF (M(I,J) .EQ. 1.0) THEN
               N1 = N1 + 1
            ELSE
               NX = NX + 1
            END IF
 11      CONTINUE
 10   CONTINUE
      WRITE (6,'(A,A)') 'file:          ', FNAME(1:LEN_TRIM(FNAME))
      WRITE (6,'(A,I0)') 'BITPIX:        ', MBITPIX
      WRITE (6,'(A,I0,A,I0)') 'size:          ', MCOL, ' x ', MROW
      WRITE (6,'(A,I0,A,I0)') 'CNPIX1,CNPIX2: ', MSC, ',', MSR
      WRITE (6,'(A,I0)') 'data offset:   ', IOFF
      WRITE (6,'(A,I0)') 'value 0 (masked): ', N0
      WRITE (6,'(A,I0)') 'value 1 (good):   ', N1
      WRITE (6,'(A,I0)') 'other values:     ', NX
      WRITE (6,'(A,F8.5)') 'masked fraction:  ',
     $     N0/(FLOAT(MCOL)*MROW)

      IF (IC .GT. 0) THEN
         IF (IC .GT. MCOL .OR. IR .LT. 1 .OR. IR .GT. MROW) THEN
            WRITE (0,*) 'maskinfo: pixel outside the mask'
            STOP 1
         END IF
         NB0 = 0
         DO 20 J = MAX(1,IR-IH), MIN(MROW,IR+IH)
            DO 21 I = MAX(1,IC-IH), MIN(MCOL,IC+IH)
               IF (M(I,J) .EQ. 0.0) NB0 = NB0 + 1
 21         CONTINUE
 20      CONTINUE
         WRITE (6,'(A,I0,A,I0,A,G0)') 'value at (', IC, ',', IR,
     $        '): ', M(IC,IR)
         WRITE (6,'(A,I0,A,I0)') 'zeros in box of half-width ', IH,
     $        ': ', NB0
         WRITE (6,'(A,I0,A)') 'box, top row = row ', MIN(MROW,IR+IH),
     $        ", '0' = masked:"
         DO 30 J = MIN(MROW,IR+IH), MAX(1,IR-IH), -1
            LINE = ' '
            DO 31 I = MAX(1,IC-IH), MIN(MCOL,IC+IH)
               IF (M(I,J) .EQ. 0.0) THEN
                  LINE(I-MAX(1,IC-IH)+1:I-MAX(1,IC-IH)+1) = '0'
               ELSE
                  LINE(I-MAX(1,IC-IH)+1:I-MAX(1,IC-IH)+1) = '.'
               END IF
 31         CONTINUE
            WRITE (6,'(A)') LINE(1:LEN_TRIM(LINE))
 30      CONTINUE
      END IF
      END
