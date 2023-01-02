import pyaudio
import time
import argparse
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Records an 8-bit raw sample straight from your microphone or what have you. It also normalizes and truncates the beginning of the sample!")
parser.add_argument("output_file", type=argparse.FileType("w"),help="The name of the recorded file")
parser.add_argument("length", type=int,help="How long to record for, in milliseconds")
parser.add_argument("sample_rate",type=int,help="Sample rate of the file")
parser.add_argument("start_threshold",type=int,help="How loud the beginning of the sample needs to be before truncation (0-127)")
parser.add_argument("end_threshold",type=int,help="How many quiet bytes are encountered before truncating the end * 255")
parser.add_argument("sensitivity",type=int,help="How sensitive the silence detection is. 0 is least sensitive, 5 is recommended for general usage.")

args=parser.parse_args()

output_file=args.output_file.name
sensitivity=args.sensitivity+1
sample_rate=args.sample_rate
length=args.length
start_threshold=args.start_threshold//sensitivity
end_threshold=255*args.end_threshold
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
    if isinstance(prefs["buffer_size"],int):
        stutter=prefs["buffer_size"]

print("Record v1.0.0")
print("by Presley Peters, 2022")
print()

if sample_rate<2000:
    print("Error: Sample rate cannot be below 2000!")
elif sample_rate>48000:
    print("Error: Sample rate cannot be above 48000!")
elif length<20:
    print("Error: Length must be above 20 milliseconds!")
elif length>10000:
    print("Error: Length must be 10000 milliseconds or below!")
elif start_threshold>127//sensitivity:
    print("Error: Start threshold must be below " + str(127//sensitivity) + "!")
elif start_threshold<0:
    print("Error: Start threshold cannot be negative!")
elif sensitivity<0:
    print("Error: End sensitivity cannot be negative!")
elif sensitivity>255:
    print("Error: End sensitivity must be 255 or below!")
elif end_threshold>length*sample_rate:
    print("Error: End threshold must be within the range of the sample! (" + str(length*sample_rate*255) + ")")
elif end_threshold<0:
    print("Error: End threshold cannot be negative!")
else:
    print("Recording...")

    pya=pyaudio.PyAudio()
    
    frames=2**stutter
    recorded_file=[]
    stream=pya.open(frames_per_buffer=frames,format=pyaudio.paInt16,rate=sample_rate,input=True,channels=1)
    
    for a in range(0,int(sample_rate/frames*(length/1000))):
        data=stream.read(frames)
        for byte in data:
            recorded_file.append(byte)
    stream.stop_stream()
    stream.close()

    recorded_file_quantized=[]
    normalize_factor=0
    truncate_point=0
    truncate_point_found=False
    truncate_end_point=len(recorded_file)
    truncate_end_point_found=False
    quiet_bytes=0
    for a in range(0,len(recorded_file),2):
        byte=recorded_file[a+1]
        if byte>127: # it's a negative number
            byte-=127
        else: # it's a positive number, 0-127
            byte+=127
        recorded_file_quantized.append(byte)
        # ^ that bit of code took me 6 hours to work out

        # then convert it to signed
        byte-=127
        byte=abs(byte)
        byte_reduced=byte//sensitivity
        if byte>normalize_factor: # find the largest value (loudest point), positive or negative
            normalize_factor=byte
        if byte_reduced>start_threshold and not truncate_point_found:
            truncate_point=a//2
            truncate_point_found=True

        # try and trim off any silence at the end
        if truncate_point_found:
            if byte_reduced==0:
                quiet_bytes+=1
            else:
                quiet_bytes=0
            if quiet_bytes>end_threshold and not truncate_end_point_found:
                truncate_end_point=a//2
                truncate_end_point_found=True
            
    print("Normalizing...")
    normalize_factor=((127-normalize_factor)/25)+1
    for a in range(0,len(recorded_file_quantized)):
        # convert it to signed so our maths will actually work
        recorded_file_quantized[a]=127-recorded_file_quantized[a]
        recorded_file_quantized[a]*=int(normalize_factor)
        # then make it unsigned again!
        recorded_file_quantized[a]+=127
        
        # no clue why it "clips" on silent bits, but this seems to fix it:
        if recorded_file_quantized[a]>255:
            recorded_file_quantized[a]=255
        elif recorded_file_quantized[a]<0:
            recorded_file_quantized[a]=0
            
    print("Truncating...")
    recorded_file_quantized=recorded_file_quantized[truncate_point:truncate_end_point]
        
    with open(output_file, "wb") as file:
        file.write(bytearray(recorded_file_quantized))
                    
    stream=pya.open(format=pyaudio.paUInt8,rate=sample_rate,output=True,channels=1,frames_per_buffer=2**stutter)

    print("Playing...")
    for byte in recorded_file_quantized:
        stream.write(int.to_bytes(byte,1,"little"))

    stream.stop_stream()
    stream.close()
    pya.terminate()
