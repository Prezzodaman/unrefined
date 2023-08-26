import pyaudio
import argparse
import math
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Stops the waveform from going above a certain amplitude")
parser.add_argument("input_file", type=argparse.FileType("r"),help="The name of the file to chop")
parser.add_argument("output_file", type=argparse.FileType("w"),help="The name of the chopped file")
parser.add_argument("sample_rate",type=int,help="Sample rate of the file (only used for playback)")
parser.add_argument("amplitude",type=int,help="The amplitude to cut below")
parser.add_argument("-i", "--invert", action="store_true", help="Inverts the waveform instead of clipping it")

args=parser.parse_args()

file_name=args.input_file.name
output_file=args.output_file.name
sample_rate=args.sample_rate
amplitude=args.amplitude
invert=args.invert
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
	if isinstance(prefs["buffer_size"],int):
		stutter=prefs["buffer_size"]

print("Topper v1.0.0")
print("by Presley Peters, 2023")
print()

if sample_rate<2000:
	print("Error: Sample rate cannot be below 2000!")
elif sample_rate>100000:
    print("Error: Sample rate cannot be above 100000!")
elif amplitude>255:
    print("Error: Amplitude cannot be above 255!")
elif amplitude<0:
    print("Error: Amplitude cannot be below 0!")
else:
	file_orig=[]
	with open(file_name, "rb") as file:
		file_orig=file.read()

	file_finished=[]

	for byte in file_orig:
		if byte>amplitude:
			if invert:
				byte_actual=(0-byte)+((amplitude-127)+255)
				if byte_actual<0:
					byte_actual=0
				if byte_actual>255:
					byte_actual=255
				file_finished.append(byte_actual)
			else:
				file_finished.append(amplitude)
		else:
			file_finished.append(byte)

	with open(output_file, "wb") as file:
		file.write(bytearray(file_finished))

	pya=pyaudio.PyAudio()
					
	stream=pya.open(format=pyaudio.paUInt8,rate=sample_rate,output=True,channels=1,frames_per_buffer=2**stutter)

	print("Playing...")
	for byte in file_finished:
		stream.write(int.to_bytes(byte,1,"little"))

	stream.stop_stream()
	stream.close()
	pya.terminate()
