import argparse
import pyaudio
import math
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Additive synthesis")
parser.add_argument("file", type=argparse.FileType("w"),help="The name of the resulting file")
parser.add_argument("sample_rate",type=int,help="Sample rate")
parser.add_argument("frequency",type=int,help="Base frequency (hz)")
parser.add_argument("spacing",type=int,help="Frequency spacing (hz)")
parser.add_argument("passes",type=int,help="How many frequencies to add")
parser.add_argument("reduction",type=int,help="How much to reduce the volume on each iteration")
parser.add_argument("length",type=int,help="Length in seconds")
parser.add_argument("-sb", "--sixteen_bit", action="store_true", help="Renders the file in 16-bit")

args=parser.parse_args()

file_name=args.file.name
sample_rate=args.sample_rate
length=args.length
frequency=args.frequency
spacing=args.spacing
iterations=args.passes
reduction=args.reduction
sixteen_bit=args.sixteen_bit
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
	if isinstance(prefs["buffer_size"],int):
		stutter=prefs["buffer_size"]

print("Additive v1.0.0")
print("by Presley Peters, 2023")
print()

if sample_rate<2000:
	print("Error: Sample rate cannot be below 2000!")
elif frequency>sample_rate/2:
	print("Error: Sample rate cannot be above " + str(frequency*2) + "!")
else:
	file_length_samples=int(args.length*sample_rate)
	if sixteen_bit:
		file_finished=[0]*file_length_samples
	else:
		file_finished=[0]*(file_length_samples//2)

	angle=0
	reduction_byte=0
	for iteration in range(0,iterations):
		#print("Pass " + str(iteration+1) + "/" + str(iterations) + ", Frequency " + str(frequency) + ", Reduction " + str(reduction_byte))
		print("Pass " + str(iteration+1) + "/" + str(iterations) + "...", end="\r")
		for position in range(0,file_length_samples,2):
			byte=(int((math.sin(angle)*(32768-reduction_byte))+32768))//iterations
			if sixteen_bit:
				file_finished[position]+=byte
			else:
				file_finished[position//2]+=byte
			angle+=(frequency*math.pi*2)/sample_rate
		frequency+=spacing
		if reduction_byte<32768:
			reduction_byte+=reduction*2
		else:
			reduction_byte=32768
	print()

	if sixteen_bit:
		for position in range(0,file_length_samples,2):
			byte=(file_finished[position]+32768) & 65535
			file_finished[position]=byte & 255
			file_finished[position+1]=byte>>8
	else:
		for position in range(0,file_length_samples//2):
			file_finished[position]=file_finished[position]>>8

	with open(file_name,"wb") as file:
		file.write(bytearray(file_finished))

	pya=pyaudio.PyAudio()
					
	stream=pya.open(format=pyaudio.paInt16,rate=sample_rate,output=True,channels=1,frames_per_buffer=2**stutter)

	print("Playing...")
	if sixteen_bit:
		for position in range(0,file_length_samples,2):
			byte=file_finished[position] | (file_finished[position+1]<<8)
			stream.write(int.to_bytes(byte,2,"little"))
	else:
		for byte in file_finished:
			stream.write(int.to_bytes(byte,1,"little"))

	stream.stop_stream()
	stream.close()
	pya.terminate()
