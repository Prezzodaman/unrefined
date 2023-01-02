import pyaudio
import argparse
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Makes a sample louder or quieter")
parser.add_argument("input_file", type=argparse.FileType("r"),help="The name of the file to affect")
parser.add_argument("output_file", type=argparse.FileType("w"),help="The name of the affected file")
parser.add_argument("sample_rate",type=int,help="Sample rate of the file (only used for playback)")
parser.add_argument("loudness",type=float,help="How loud to make the sample. 1 is normal volume, 0.5 is half volume, 2 is double the volume.")

args=parser.parse_args()

file_name=args.input_file.name
output_file=args.output_file.name
sample_rate=args.sample_rate
loudness=args.loudness
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
    if isinstance(prefs["buffer_size"],int):
        stutter=prefs["buffer_size"]

print("Loudness v1.0.0")
print("by Presley Peters, 2022")
print()

if sample_rate<2000:
    print("Error: Sample rate cannot be below 2000!")
elif sample_rate>100000:
    print("Error: Sample rate cannot be above 100000!")
elif loudness>8:
    print("Error: Loudness cannot be greater than 8!")
elif loudness<0.0125:
    print("Error: Loudness must be greater than 0.0125!")
else:
    file_orig=[]
    with open(file_name, "rb") as file:
        file_orig=file.read()

    file_finished=[]
    for byte in file_orig:
        byte_amplified=int(((127-byte)*loudness)+127)
        if byte_amplified<0:
            byte_amplified=0
        if byte_amplified>255:
            byte_amplified=255
        file_finished.append(byte_amplified)

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
