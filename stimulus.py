from math import pi as pi
import numpy as np
from numpy import log as log
from numpy import exp as exp
from numpy import sin as sin
from numpy import cos as cos
from scipy import signal
from scipy.signal import fftconvolve

class stimulus:

    # Constructor
    def __init__(self,stimulusType, samplingRate):

        self.type = stimulusType
        self.fs = samplingRate
        self.repetitions = 0
        self.Lp = []
        self.signal = []
        self.invfilter = []

    # Generate the stimulus and set requred attributes
    def generate(self, fs, duration, amplitude, repetitions, silenceAtStart, silenceAtEnd,sweeprange):

        if self.type == 'sinesweep':

            f1 = np.max((sweeprange[0],1))             # start of sweep in Hz.
            if sweeprange[1] == 0:
                f2 = int(fs/2)      # end of sweep in Hz. Sweep till Nyquist to avoid ringing
            else:
                f2 = sweeprange[1]

            w1 = 2*pi*f1/fs     # start of sweep in rad/sample
            w2 = 2*pi*f2/fs     # end of sweep in rad/sample

            numSamples = duration*fs
            sinsweep = np.zeros(shape = (numSamples,1))
            taxis = np.arange(0,numSamples,1)/(numSamples-1)

            # for exponential sine sweeping
            lw = log(w2/w1)
            sinsweep = amplitude * sin(w1*(numSamples-1)/lw * (exp(taxis*lw)-1));

            # Find the last zero crossing to avoid the need for fadeout
            # Comment the whole block to remove this
            k = np.flipud(sinsweep)
            error = 1
            counter = 0
            while error > 0.001:
                error = np.abs(k[counter])
                counter = counter+1

            k = k[counter::]
            sinsweep_hat = np.flipud(k)
            sinsweep = np.zeros(shape = (numSamples,))
            sinsweep[0:sinsweep_hat.shape[0]] = sinsweep_hat

            # the convolutional inverse
            envelope = (w2/w1)**(-taxis); # Holters2009, Eq.(9)
            invfilter = np.flipud(sinsweep)*envelope
            scaling = pi*numSamples*(w1/w2-1)/(2*(w2-w1)*log(w1/w2))*(w2-w1)/pi; # Holters2009, Eq.10

            # fade-in window. Fade out removed because causes ringing - cropping at zero cross instead
            taperStart = signal.windows.tukey(numSamples,0)
            taperWindow = np.ones(shape = (numSamples,))
            taperWindow[0:int(numSamples/2)] = taperStart[0:int(numSamples/2)]
            sinsweep = sinsweep*taperWindow

            # Final excitation including repetition and pauses
            sinsweep = np.expand_dims(sinsweep,axis = 1)
            zerostart = np.zeros(shape = (silenceAtStart*fs,1))
            zeroend = np.zeros(shape = (silenceAtEnd*fs,1))
            sinsweep = np.concatenate((np.concatenate((zerostart, sinsweep), axis = 0), zeroend), axis=0)
            sinsweep = np.transpose(np.tile(np.transpose(sinsweep),repetitions))

            # Set the attributes
            self.Lp = (silenceAtStart + silenceAtEnd + duration)*fs;
            self.invfilter = invfilter/amplitude**2/scaling
            self.repetitions = repetitions
            self.signal = sinsweep

        else:

            raise NameError('Excitation type not implemented')
            return


    def deconvolve(self,systemOutput):

        if self.type == 'sinesweep':

            numChans = systemOutput.shape[1]
            tmplen = self.invfilter.shape[0] + self.Lp-1;
            RIRs = np.zeros(shape = (tmplen,numChans))

            for idx in range(0,numChans):

                #currentChannel = systemOutput[0:self.repetitions*self.Lp,idx]
                currentChannel = systemOutput[:,idx]
                # RIRs[:,idx] = fftconvolve(self.invfilter,currentChannel);

                # Average over the repetitions - DEPRECATED. Should not be done.
                sig_reshaped = currentChannel.reshape((self.repetitions,self.Lp))
                sig_avg = np.mean(sig_reshaped,axis = 0)

                # Deconvolution
                RIRs[:,idx] = fftconvolve(self.invfilter,sig_avg);

            return RIRs

        else:

            raise NameError('Excitation type not implemented')
            return

# End of class definition
# ===========================================================================
# ===========================================================================
# NON-CLASS FUNCTIONS

def test_deconvolution(args):

    type = 'sinesweep'
    fs = args.fs
    duration = args.duration
    amplitude = args.amplitude
    repetitions = args.reps
    silenceAtStart = args.startsilence
    silenceAtEnd = args.endsilence
    sweeprange = args.sweeprange

    if repetitions > 1:
        raise NameError('Synchronous time averaging is not recommended for exponential sweeps. A suitable averaging method is not implemented. Please use a single long sine sweep (e.g. 15 sec.)')

    # Create a test signal object, and generate the excitation
    testStimulus = stimulus(type,fs);
    testStimulus.generate(fs, duration, amplitude,repetitions,silenceAtStart, silenceAtEnd,sweeprange)
    deltapeak = testStimulus.deconvolve(testStimulus.signal)
    startid = duration*fs + silenceAtStart*fs -150
    deltapeak = deltapeak[startid:startid + 300]

    return deltapeak
