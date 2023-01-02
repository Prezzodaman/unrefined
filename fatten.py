import pyaudio
import time
import argparse
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Makes a sample sound FAT.")
parser.add_argument("input_file", type=argparse.FileType("r"),help="The name of the file to fatten")
parser.add_argument("output_file", type=argparse.FileType("w"),help="The name of the obese file")
parser.add_argument("sample_rate",type=int,help="Sample rate of the file (only used for playback)")

args=parser.parse_args()

file_name=args.input_file.name
output_file=args.output_file.name
sample_rate=args.sample_rate
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
    if isinstance(prefs["buffer_size"],int):
        stutter=prefs["buffer_size"]
        
print("Fatten v1.0.0")
print("by Presley Peters, 2022")#
print("\"LET'S BEEF IT UP.\"")
print()

if sample_rate<2000:
    print("Error: Sample rate cannot be below 2000!")
elif sample_rate>100000:
    print("Error: Sample rate cannot be above 100000!")
else:
    print("Rendering file...")

    with open(file_name, "rb") as file:
        file_orig=file.read()
    file_orig_2=list(file_orig).copy() # so the REAl orig is unaffected
        
    start_time=time.perf_counter()

    # Inverting a low-passed version of a sample into the normal version gives you a high-pass.
    # The theory (I haven't programmed this yet) is that I can get just the low-passed version and mix it with the high-passed version, to give the bass and treble a boost, while keeping the mids as-is.

    passes=127 # hard-coded because no other value gives the desired effect ;)

    # Low-pass it...

    file_lowpass_onepass=[]
    for a in range(0,passes):
        file_lowpass=[]
        previous_byte=0
        for byte in file_orig_2:
            filtered_byte=(byte+previous_byte)//2 # this is literally it.
            file_lowpass.append(filtered_byte)
            previous_byte=byte
        if a==passes//2:
            file_lowpass_onepass=file_lowpass.copy()
        file_orig_2=file_lowpass.copy()
        
    # High-pass it...
    file_highpass=[]
    # would you believe I only discovered zip and enumerate yesterday? (29/12/2022) absolute game changers!!!
    for byte_orig,byte_lowpass in zip(file_orig,file_lowpass):
        byte=(byte_orig-abs(0-byte_lowpass))+127
        if byte<0:
            byte=0
        if byte>255:
            byte=255
        file_highpass.append(byte)

    # Mix 'em together...
    file_finished=[]
    for byte_lowpass,byte_highpass in zip(file_lowpass_onepass,file_highpass):
        file_finished.append((byte_lowpass+byte_highpass)//2)

    end_time=time.perf_counter()
        
    print("File rendered in " + str(round(end_time-start_time,2)) + " seconds!")

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
