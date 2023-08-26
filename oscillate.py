import argparse
import pyaudio
import math
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Produces a constant/sweeping tone")
parser.add_argument("file", type=argparse.FileType("w"),help="The name of the resulting file")
parser.add_argument("sample_rate",type=int,help="Sample rate")
parser.add_argument("frequency",type=int,help="Frequency of oscillation (hz)")
parser.add_argument("length",type=int,help="Length in seconds")
parser.add_argument("-sq", "--square", action="store_true", help="Uses a square wave instead of a sine wave")
parser.add_argument("-sw", "--sweep",type=int,default=0,help="Sweeps the tone up or down, increasing the frequency by a certain amount. Positive values increase the frequency, negative values decrease it.")
parser.add_argument("-sb", "--sixteen_bit", action="store_true", help="Renders the file in 16-bit")

args=parser.parse_args()

file_name=args.file.name
sample_rate=args.sample_rate
frequency=args.frequency
length=args.length
square=args.square
sweep=args.sweep
sixteen_bit=args.sixteen_bit
length_samples=length*sample_rate
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
	if isinstance(prefs["buffer_size"],int):
		stutter=prefs["buffer_size"]

print("Oscillate v1.0.0")
print("by Presley Peters, 2023")
print()

if sample_rate<2000:
	print("Error: Sample rate cannot be below 2000!")
elif frequency>sample_rate/2:
	print("Error: Sample rate cannot be above " + str(frequency*2) + "!")
else:
	file_finished=[]

	# 0.1 @ 11025 = 175hz
	# 0.2 @ 11025 = 345hz
	# 0.3 @ 11025 = 525hz
	# 0.4 @ 11025 = 690hz
	# I FOUND THE FORMULA!

	angle=0
	for a in range(0,length_samples):
		byte=int((math.sin(angle)*32768)+32768)
		byte_actual=byte
		if square:
			if byte>=32768:
				byte_actual=32768
			elif byte<32768:
				byte_actual=0
		else:
			if byte_actual>65535:
				byte_actual=65535
			if byte_actual<0:
				byte_actual=0
		if sixteen_bit:
			byte_actual=(byte_actual+32768) & 65535
			file_finished.append(byte_actual & 255)
			file_finished.append(byte_actual>>8)
		else:
			file_finished.append(byte_actual>>8)
		angle+=(frequency*math.pi*2)/sample_rate
		frequency+=sweep/(sample_rate/4)

	with open(file_name, "wb") as file:
		file.write(bytearray(file_finished))

	pya=pyaudio.PyAudio()
					
	stream=pya.open(format=pyaudio.paInt16,rate=sample_rate,output=True,channels=1,frames_per_buffer=2**stutter)

	print("Playing...")
	if sixteen_bit:
		for position in range(0,length_samples*2,2):
			byte=file_finished[position] | (file_finished[position+1]<<8)
			stream.write(int.to_bytes(byte,2,"little"))
	else:
		for byte in file_finished:
			stream.write(int.to_bytes(byte,1,"little"))

	stream.stop_stream()
	stream.close()
	pya.terminate()
