import tkinter

def scroll_all_listboxes(*a):
    for listbox in track_listboxes:
        listbox.yview(*a)

window=tkinter.Tk()
window.geometry("600x400")
window.title("UnrefinedTracker v1.0.0 alpha")
window.resizable(width=False,height=False)

pattern_editor=tkinter.Frame(window,width=400,height=400)
pattern_editor.grid(row=0,column=0,sticky="w")
parameters=tkinter.Frame(window,width=200,height=400)
parameters.grid(row=0,column=1,sticky="e")

scrollbar=tkinter.Scrollbar(pattern_editor)

track_listboxes=[]
tracks=4
track_length=64
for a in range(0,tracks):
    track_listboxes.append(tkinter.Listbox(pattern_editor))
for listbox in track_listboxes:
    listbox.pack(side="left",fill="y")
    for a in range(0,track_length):
        listbox.insert("end","00 00 00 00")
    listbox.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=scroll_all_listboxes)
scrollbar.pack(side="right",fill="y")

tkinter.Checkbutton(parameters,text="Reverse").pack()

window.mainloop()
