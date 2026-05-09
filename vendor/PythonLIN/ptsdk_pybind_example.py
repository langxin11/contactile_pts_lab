import time

import PTSDK_CXX_Pybind

if __name__ == '__main__':

    isMultithreadedExample = True

    isLogging = True

    # COM port 
    port = "/dev/ttyACM0"
    rate = 115200
    parity = 0
    byteSize = '\u0008'
    isFlush = True

    # Initialise sensors
    sen0 = PTSDK_CXX_Pybind.PTSDKSensor()
    sen1 = PTSDK_CXX_Pybind.PTSDKSensor()

    # Initialise listener and add sensors
    listener = PTSDK_CXX_Pybind.PTSDKListener(isLogging)
    listener.addSensor(sen0)
    listener.addSensor(sen1)

    if isMultithreadedExample:
        # Multi-threaded example
        pillarInd = 0
        s0p0disp = [0,0,0]

        # Connect to COM port and start listening
        res = listener.connectAndStartListening(port, rate, parity, byteSize, isFlush)
        if res == 0:
            print('main(): Successfully connected COM port and starting to listen')
        else:
            print('main(): FAILED to connect to COM port and start to listen')
            exit()

        # Send a BIAS request
        res = listener.sendBiasRequest()
        if res:
            print('main(): Successfully sent a BIAS request')
        else:
            print('main(): FAILED to send a BIAS request')
            exit()
            
        # Setting the controller sampling rate
        res = listener.setSamplingRate(PTSDK_CXX_Pybind.PTSDKConstants.SAMP_RATE_500)
        if res:
            print('main(): Successfully set the sampling rate')
        else:
            print('main(): FAILED to set the sampling rate')
            exit()

        # User application code - do somethig with the data
        # Accessing data from a whole sensor
        for i in range(0,10):
            force = sen0.getGlobalForce() # Get XYZ Global Force from SEN0
            for dimInd in range(0,PTSDK_CXX_Pybind.PTSDKConstants.NDIM):
                print('S0: global F' + str(dimInd) + ' = ' + str(force[dimInd]))
            time.sleep(1)
        for i in range(0,10):
            s1disp = sen1.getAllDisplacements() # Get XYZ displacements of all pillars of SEN1
            for pillarInd in range(0,sen1.getNPillar()):
                    print('S1P' + str(pillarInd) + ': D0 = ' + str(s1disp[0][pillarInd]) + ', D1 = ' + str(s1disp[1][pillarInd]) + ', D2 = ' + str(s1disp[2][pillarInd]))
            time.sleep(1)
        # Accessing data from a single pillar
        pillarInd = 3
        for i in range(0,10):
            force = sen0.getPillarDisplacements(pillarInd) # Get P3 force from SEN0
            for dimInd in range(0,PTSDK_CXX_Pybind.PTSDKConstants.NDIM):
                print('S0P3: F' + str(dimInd) + ': ' + str(force[dimInd]))
            time.sleep(1)
        # Performing slip detection and estimating friction
        res = listener.startSlipDetection() # Start slip detection
        if res:
            print('main(): Successfully started slip detection')
        else:
            print('main(): FAILED to start slip detection')
            exit()
        isSlipDetectionActive, isRefPillarLoaded, contactStates, slipStates = sen0.getAllSlipStatus() # Get slip states of all pillars in SEN0
        for pillarInd in range(0,sen0.getNPillar()):
            print('S0_P' + str(pillarInd) + ':')
            match slipStates[pillarInd]:
                case PTSDK_CXX_Pybind.PTSDKConstants.INELIGIBLE:
                    print('\tWas not in contact at slip detection start.')
                case PTSDK_CXX_Pybind.PTSDKConstants.CONTACT_AT_START:
                    print('\tIn contact rom slip detection start.')
                case PTSDK_CXX_Pybind.PTSDKConstants.LOST_CONTACT:
                    print('\tLost contact.')
                case PTSDK_CXX_Pybind.PTSDKConstants.TLOADING:
                    print('\tIs being tangentially loaded.')
                case PTSDK_CXX_Pybind.PTSDKConstants.SLIPPED:
                    print('\tSlipped.')
        friction = sen0.getFrictionEstimate() # Get the current friction estimate of SEN0
        print('S0: friction estimate = ' + str(friction))
        res = listener.startSlipDetection() # Stop slip detection
        if res:
            print('main(): Successfully stopped slip detection')
        else:
            print('main(): FAILED to stop slip detection')
            exit()
            
        # Stop listening and disconnect from COM port
        listener.stopListeningAndDisconnect()

    else:
        # Single thread example
        isFlush = True
        pillarInd = 0
        s0p0forces = [0,0,0]
        
        # Connect to the COM port
        res = listener.connect(port, rate, parity, byteSize)
        if res == 0:
            print('main(): Successfully connected to the COM port')
        else:
            print('main(): FAILED to connect to the COM port and start to listen')
            exit()

        
        # Read the next sample
        for i in range(0,1000):
            res = listener.readNextSample(True)
            if res:
                print("main(): Successfully read the next sample")
            else:
                print("main(): FAILED to readthe next sample")
                break
            # User application code - do something with the data
            s0p0forces = sen0.getPillarForces(pillarInd)
            if i%100 == 0:
                for dimInd in range(0,PTSDK_CXX_Pybind.PTSDKConstants.NDIM):
                    print('S0P0: F' + str(dimInd) + ': ' + str(s0p0forces[dimInd]))
        
        # Disconnect from the COM port
        listener.disconnect()
        
    pass
