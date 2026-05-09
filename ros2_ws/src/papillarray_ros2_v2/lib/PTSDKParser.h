#ifndef PTSDKPARSER_H
#define PTSDKPARSER_H
#endif

#ifdef _WIN32
#ifndef PTSDK_CPP_LIB_H
#include "PTSDK_CPP_LIB.h"
#endif
#endif

#ifndef PTSDKSENSOR_H
#include "PTSDKSensor.h"
#endif

#ifndef PTSDKCONSTANTS_H
#include "PTSDKConstants.h"
#endif

#include <stdio.h>

#ifdef _WIN32
#include <windows.h>
#endif
#ifndef _WIN32
#include <cstddef>
#include <cstdint>
#include <stdint.h>
#define BYTE unsigned char
#define DWORD uint32_t
#endif

#define STARTBYTE0 		0x55		// The first byte of the start packet
#define STARTBYTE1 		0x66		// The second byte of the start packet
#define STARTBYTE2 		0x77		// The third byte of the start packet
#define STARTBYTE3 		0x88		// The fourth byte of the start packet
#define ENDBYTE0		0xAA		// The first byte of the end packet
#define ENDBYTE1		0xBB		// The second byte of the end packet
#define ENDBYTE2		0xCC		// The third byte of the end packet
#define ENDBYTE3		0xDD		// The fourth byte of the end packet

#define NBYTES_STARTPACKET		4		// Number of bytes in the start packet
#define NBYTES_ENDPACKET		4		// Number of bytes in the end packet

#define MAX_DATAPACKETLEN	2048		// Maximum number of bytes in the data packet (the actual number of bytes may be variable)
#define BIGARRAY_LEN		100000		// 

using namespace std;

/** \brief The PTSDKParser class describes a parser for the data packet transmitted from a Controller with a number of PapillArray Tactile Sensors connected.
 *
 * The PTSDKParser class describes a parser for the data packet transmitted from a Controller with a number of PapillArray Tactile Sensors connected.
 *
 * @author Contactile Pty Ltd
 * @version December 2022
 */
#ifdef _WIN32
class PTSDK_CPP_LIB_API PTSDKParser {
#else
class PTSDKParser {
#endif

	//friend class PTSDKListener;

private:

	/* Private member variables */

	uint32_t sampleCounter;			// The sample number (since connecting)
	uint32_t nDataPacket;			// The number of valid bytes in the dataPacketBuf
	BYTE* dataPacketBuf;			// A buffer containing the data packet read from the COM port (length: MAX_DATAPACKETLEN)

	int nSensor;								// The number of sensors connected to the communications hub
	PTSDKSensor* pSensors[MAX_NSENSOR];			// Sensors connected to the communications hub

	unsigned int waitingForStartByteNum;		// The number of start bytes to look for
	unsigned int waitingForEndByteNum;			// The number of end bytes to look for

	const BYTE startBytes[NBYTES_ENDPACKET] = {(BYTE) STARTBYTE0, (BYTE) STARTBYTE1, (BYTE) STARTBYTE2, (BYTE) STARTBYTE3};	// The bytes to match to a start packet from the controller
	const BYTE endBytes[NBYTES_ENDPACKET] = {(BYTE) ENDBYTE0, (BYTE) ENDBYTE1, (BYTE) ENDBYTE2, (BYTE) ENDBYTE3};			// The bytes to match to an end packet from the controller

	/* Private helper functions */

	bool validateChecksum(IN const BYTE* dataPacketBuf, IN const uint32_t nDataPacketBuf, IN uint32_t checksum_index);

	/* Utility functions - To be moved to a super class(common to all Parser child classes in the fuuture */

	void unpackAddress(IN const BYTE data[MAX_DATAPACKETLEN], IN OUT uint32_t* pByteInd, IN uint16_t addressSize, IN OUT uint32_t* pVal);
	void unpackUint8(IN const BYTE data[MAX_DATAPACKETLEN], IN OUT uint32_t* pByteInd, OUT uint8_t* pVal);
	void unpackUint16(IN const BYTE data[MAX_DATAPACKETLEN], IN OUT uint32_t* pByteInd, OUT uint16_t* pVal);
	void unpackUint32(IN const BYTE data[MAX_DATAPACKETLEN], IN OUT uint32_t* pByteInd, OUT uint32_t* pVal);
	void unpackUint64(IN const BYTE data[MAX_DATAPACKETLEN], IN OUT uint32_t* pByteInd, OUT uint64_t* pVal);
	void unpackInt8(IN const BYTE data[MAX_DATAPACKETLEN], IN OUT uint32_t* pByteInd, OUT int8_t* pVal);
	void unpackFloat(IN const BYTE data[MAX_DATAPACKETLEN], IN OUT uint32_t* pByteInd, OUT float* pVal);
	void unpackDouble(IN const BYTE data[MAX_DATAPACKETLEN], IN OUT uint32_t* pByteInd, OUT double* pVal);

public:

	/* Constructors */

	/**
	 * Constructor.
	 */
	PTSDKParser(void);

	/* Destructors */

	/**
	 * Destructor.
	 */
	~PTSDKParser(void);

	/** 
	 * Add the character to the dataPacketBuf and determine if we now have a complete data packet
	 */
	bool addInputByte(BYTE b);

	/**
	 * Convert byte data to values and add to Sensors
	 */
	bool parseDataPacket(void);

	/**
	 * Copy Sensor data to pSensorsDest and reset dataPacketBuf 
	 */
	void copyAndResetSample(OUT PTSDKSensor *pSensorsDest[MAX_NSENSOR]);

};
