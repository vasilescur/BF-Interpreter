# Define constants
MEMORY_SIZE = 1000


""" ------- Reader ------- """

# Open the source file and read its characters into an instruction array
sourceFile = open(input("Source file: "))

instructions = []

for line in sourceFile.readlines():
	for x in range(0, len(line)):
		if line[x] in ["+", "-", "<", ">", ".", ",", "[", "]"]:
			instructions.append(line[x])
			
sourceFile.close()

	
""" ------- Loop Lookaheads ------- """

# Find jump points
loopStarts = []
loopEnds = []

for x in range(0, len(instructions)):
	if instructions[x] == "[":
		loopStarts.append(x)
	elif instructions[x] == "]":
		loopEnds.append(x)



""" ------- Initializations ------- """

# Create memory array and fill with 0's
memory = []

for x in range(1, MEMORY_SIZE):
	memory.append(0)

# Get runtime and pointers ready
stillRunning = True
memPointer = 0
insPointer = 0

currentLoopStack = []



""" ------- Main Loop ------- """

# Main interpreter loop
while stillRunning:
	if instructions[insPointer] == "+":
		if memory[memPointer] == 255:
			memory[memPointer] = 0
		else:
			memory[memPointer] += 1
	
	elif instructions[insPointer] == "-":
		if memory[memPointer] == 0:
			memory[memPointer] = 255
		else:
			memory[memPointer] -= 1
	
	elif instructions[insPointer] == ">":   # If not at end, move right
		if memPointer >= MEMORY_SIZE:
			print("Error: Memory pointer out of bounds.")
		else:
			memPointer += 1
	
	elif instructions[insPointer] == "<":   # If not at 0, move left
		if memPointer == 0:
			print("Error: Memory pointer out of bounds.")
		else:
			memPointer -= 1
	
	elif instructions[insPointer] == ".":
		print(chr(memory[memPointer]), end="")  # ASCII; no space after
	
	elif instructions[insPointer] == ",":
		memory[memPointer] = ord(input())   # input --> ASCII

	elif instructions[insPointer] == "[":   # Make sure memory[memPointer] is non-zero
		if memory[memPointer] != 0: 	# Push the current loop start to the current loop stack
			currentLoopStack.append(loopStarts.index(insPointer))
		else:   # Jump to end of the loop
			insPointer = loopEnds[loopStarts.index(insPointer)]
	
	elif instructions[insPointer] == "]":   # Simple jump back to matching loopStart (top of stack)
		insPointer = loopStarts[loopEnds.index(insPointer)] - 1     # -1 is to offset and force re-evaluation of [ instruction

	insPointer += 1     # Move to next instruction
	
	if insPointer >= len(instructions):     # End program
		stillRunning = False

