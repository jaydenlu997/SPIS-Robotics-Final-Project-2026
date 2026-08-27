# This is a basic program to test the camera

def SetupPICamera():
    # General libraries
    import time
    # Libraries to control the camera
    from picamera2 import Picamera2
    import cv2

    print("Setting up the camera ...")

    # Initialize the camera
    camera = Picamera2()

    # Configure the camera
    config = camera.create_video_configuration(
        #-----------------------------------------------------
        # Picam natively uses RGB, but OpenCV, which we use for manipulating
        # and displaying images, uses BGR. So we will work with BGR.
        # We can change the settings of picam to give us BGR instead, and
        # we don't need to do an explic conversion. Confusingly, "RGB888"
        # means that frames will be grabbed BGR format (and vice versa).
        #-----------------------------------------------------
        main = {"size": (640, 480), "format": "RGB888"},
    )
    camera.configure(config)

    return camera

def RunPICamera(camera):

    # Run the camera for this many seconds
    duration = 5


    # Start the camera
    camera.start()
    start_time = time.time()
    
    # Continuously grab camera frames
    print("Starting the camera ...")
    while (time.time() - start_time < duration):
        
        # Grab a frame
        img = camera.capture_array()
        
        # Show the frame (OpenCV assumes BRG color representation)
        cv2.imshow("Camera", img)
        
        # The waitKey command is needed to force openCV to show the image
        # It looks for a keystroke for x ms (with x the argument) 
        cv2.waitKey(1)
        
        

def EndPICamera(camera):
    # Clean up the resources
    print("Stopping the camera ...")
    cv2.destroyAllWindows()
    camera.stop()
    camera.close()