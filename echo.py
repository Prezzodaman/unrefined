import pyaudio
import time
import argparse
from prefs import load_prefs

parser=argparse.ArgumentParser(description="Adds a delay effect to a sample")
parser.add_argument("input_file", type=argparse.FileType("r"),help="The name of the file to reverse")
parser.add_argument("output_file", type=argparse.FileType("w"),help="The name of the finished file")
parser.add_argument("sample_rate",type=int,help="Sample rate of the file (only used for playback)")
parser.add_argument("speed",type=int,help="How many bytes until the next delay * 255")
parser.add_argument("-s","--silence",action="store_true",help="Add silence at the end of the sound, to allow time for the echo to finish decaying")

args=parser.parse_args()

file_name=args.input_file.name
output_file=args.output_file.name
sample_rate=args.sample_rate
speed=(args.speed+1)*255
silence=args.silence
stutter=1

prefs=load_prefs("prefs.cfg")
if "buffer_size" in prefs:
    if isinstance(prefs["buffer_size"],int):
        stutter=prefs["buffer_size"]

print("Echo echo echo echo... v1.0.0")
print("by Presley Peters, 2022")
print()

if sample_rate<2000:
    print("Error: Sample rate cannot be below 2000!")
elif sample_rate>100000:
    print("Error: Sample rate cannot be above 100000!")
else:
    with open(file_name, "rb") as file:
        file_orig=list(file.read())
    if silence:
        for a in range(0,speed*7):
            file_orig.append(127)
        
    if speed>len(file_orig)-1:
        print("Error: Speed out of range! Must be " + str(len(file_orig)//255) + " or below.")
    else:
        print("Rendering file...")
        
        start_time=time.perf_counter()

        file_volumes=[]
        volume_offsets=[0,2,3,3.5,3.75,3.875,3.9375,3.96875]
        for volume in range(0,8):
            file_volume=[]
            for b in range(0,(speed-255)*volume): # fill the beginning of the list with silence of incremental length
                file_volume.append(127)
            for byte in file_orig:
                file_volume.append(int((byte>>volume)+(32*(volume_offsets[volume]))))
            file_volumes.append(file_volume)

        file_finished=[]
        for position in range(0,len(file_orig)):
            sample_sum=0
            for volume in file_volumes:
                if position<len(volume):
                    sample_sum+=volume[position]
            #sample_sum=(sample_sum//2)-384 # perfect result, but half the volume
            sample_sum=(sample_sum-766-122) # near perfect result at full volume! no clue why the values are so specific
            if sample_sum>255: # just to be safe
                sample_sum=255
            if sample_sum<0:
                sample_sum=0
            file_finished.append(sample_sum)
        
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
