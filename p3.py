# Import libraries
import RPi.GPIO as GPIO
import random
from ES2EEPROMUtils import ES2EEPROM
import os
import math
from gpiozero import LED, Buzzer, PWMLED

# some global variables that need to change as we run the program
end_of_game = None  # set if the user wins or ends the game
name = ""
scores = []
count = 0
answer = 0

accuracy = None
buzzing = None

# DEFINE THE PINS USED HERE
LED_value = [11, 13, 15]
LED_accuracy = 32
btn_submit = 16
btn_increase = 18
buzzer = 33

eeprom = ES2EEPROM()

user_guess = 0


# Print the game banner
def welcome():
    os.system('clear')
    print("  _   _                 _                  _____ _            __  __ _")
    print("| \ | |               | |                / ____| |          / _|/ _| |")
    print("|  \| |_   _ _ __ ___ | |__   ___ _ __  | (___ | |__  _   _| |_| |_| | ___ ")
    print("| . ` | | | | '_ ` _ \| '_ \ / _ \ '__|  \___ \| '_ \| | | |  _|  _| |/ _ \\")
    print("| |\  | |_| | | | | | | |_) |  __/ |     ____) | | | | |_| | | | | | |  __/")
    print("|_| \_|\__,_|_| |_| |_|_.__/ \___|_|    |_____/|_| |_|\__,_|_| |_| |_|\___|")
    print("")
    print("Guess the number and immortalise your name in the High Score Hall of Fame!")


# Print the game menu
def menu():
    global end_of_game, answer
    option = input("Select an option:   H - View High Scores     P - Play Game       Q - Quit\n")
    option = option.upper()
    if option == "H":
        os.system('clear')
        print("HIGH SCORES!!")
        s_count, ss = fetch_scores()
        display_scores(s_count, ss)
    elif option == "P":
        os.system('clear')
        print("Starting a new round!")
        print("Use the buttons on the Pi to make and submit your guess!")
        print("Press and hold the guess button to cancel your game")
        answer = generate_number()
        while not end_of_game:
            pass
    elif option == "Q":
        print("Come back soon!")
        exit()
    else:
        print("Invalid option. Please select a valid one!")


def display_scores(count, raw_data):
    # print the scores to the screen in the expected format
	print("There are {} scores. Here are the top 3!".format(count))
    # print out the scores in the required format
	#for i in range(len(raw_data)):
	#	print(i + " - "+ raw_data[i-1]+ " took "+ raw_data[i]+ "guesses")
    for i in range(1, 4):
        print(i + " - "+ scores[0] + " took "+ scores[1] + " guesses")


# Setup Pins
def setup():

    global LED_value, LED_accuracy, buzzer, btn_increase, btn_submit, accuracy, buzzing, count

    # Reset relevant game variables
    count = 0
    name = "" # don't think I have to reset name as that should just get overwritten? not sure tho so just doing it anyway

    # Setup board mode
	GPIO.setmode(GPIO.BOARD)

    # Setup regular GPIO
	GPIO.setup(LED_value[0], GPIO.OUT) # channel/pin and set to output
	GPIO.setup(LED_value[1], GPIO.OUT)
	GPIO.setup(LED_value[2], GPIO.OUT)
	GPIO.setup(LED_accuracy, GPIO.OUT)

    GPIO.setup(buzzer, GPIO.OUT)

	GPIO.setup(btn_increase, GPIO.IN, pull_up_down = GPIO.PUD_UP)
	GPIO.setup(btn_submit, GPIO.IN, pull_up_down = GPIO.PUD_UP)
	
	GPIO.output(LED_value[0], GPIO.LOW) # channel/pin and set to GPIO.LOW, False, or 0
	GPIO.output(LED_value[1], GPIO.LOW)
	GPIO.output(LED_value[2], GPIO.LOW)
	GPIO.output(LED_accuracy, GPIO.LOW)

    # Setup PWM channels
	accuracy = GPIO.PWM(LED_accuracy, 50) # frequency
	accuracy.start(0) # you start PWM mode by calling start with a duty cycle from 0 to 100 percent

	buzzing = GPIO.PWM(buzzer, 1)
	buzzing.start(50)

    # Setup debouncing and callbacks
	callback_increase = ButtonHandler(btn_increase, real_cb, edge='rising', bouncetime = 100)
	callback_increase.start()
	GPIO.add_event_detect(btn_increase, GPIO.RISING, callback = btn_increase_pressed)

	callback_submit = ButtonHandler(btn_submit, realcb, edge='rising', bouncetime = 100)
	callback_submit.start()
	GPIO.add_event_detect(btn_submit, GPIO.RISING, callback = btn_guess_pressed)


# Load high scores
def fetch_scores():
	global eeprom
    # get however many scores there are
	score_count = ES2EEPROM.read_byte(eeprom, 0) # read byte from register 0
    # Get the scores
	scores = ES2EEPROM.read_block(eeprom, 1, 13) # read from block 1 because that is where the scores are
    # convert the codes back to ascii
    for i in range(0, len(scores), 4):
        scores[i] = chr(scores[i])
        scores[i+1] = chr(scores[i+1])
        scores[i+2] = chr(scores[i+2]) # each letter of name
        #scores[i+3] = scores[i+3] # the number of attempts
	# name = char(scores) # - what?
    # return back the results
    return score_count, scores


# Save high scores
def save_scores():

    global name, scores, count

    # fetch scores
	score_count, temp_scores = fetch_scores()
    # include new score
    temp_scores.append(name[0])
    temp_scores.append(name[1])
    temp_scores.append(name[2])
    temp_scores.append(count)
	# scores.add() - # add would be if was a set, which wouldn't work for our case because it will only add the element if it doesn't exiist in the set already
    # sort
    for i in range(0, len(temp_scores), 4):
        usrname = temp_scores[i] + temp_scores[i+1] + temp_scores[i+2]
        scores.append([usrname, temp_scores[i+3]])
	scores.sort(key=lambda x: x[1]) # means sort the multiple attribute list based off the attribute at x[1] in each element
    # update total amount of scores
    score_count+=1
	#score_amount = length(score)
    # write new scores
    for i in range(0, len(temp_scores), 4):
        temp_scores[i] = ord(temp_scores[i])
        temp_scores[i+1] = ord(temp_scores[i+1])
        temp_scores[i+2] = ord(temp_scores[i+2]) # each letter of name, convert back to binary
        #temp_scores[i+3] = temp_scores[i+3] # the number of attempts
    ES2EEPROM.write_byte(eeprom, 0, score_count) # write the number of scores to the byte in register 0
    ES2EEPROM.write_block(eeprom, 1, temp_scores)


# Generate guess number
def generate_number():
    return random.randint(0, pow(2, 3)-1)


# Increase button pressed
def btn_increase_pressed(channel):

    global user_guess, LED_value, LED_accuracy

    # Increase the value shown on the LEDs
	user_guess = user_guess + 1
    if user_guess == 8:
        user_guess = 0 # reset to 0 if we over 7

	if  (user_guess >= 4):
		GPIO.output(LED_value[2], True)
	else:
		GPIO.output(LED_value[2], False)

	if ((user_guess%2) == 0):
		GPIO.output(LED_value[0], False)
	else:
		GPIO.output(LED_value[0], True)

	if ((user guess == 2) or (user_guess == 3) or (user_guess == 6) or (user_guess == 7)): # hahaha hardcoding is beautiful
		GPIO.output(LED_value[1], True)
	else:
		GPIO.output(LED_value[1], False)



    # You can choose to have a global variable store the user's current guess, 
    # or just pull the value off the LEDs when a user makes a guess


# Guess button
def btn_guess_pressed(channel):

    global user_guess, name, end_of_game, btn_increase, btn_submit, answer, count

    # If they've pressed and held the button, clear up the GPIO and take them back to the menu screen
    start_time = time.time()
	while GPIO.input(btn_submit) == GPIO.LOW:
		time.sleep(0.02)
        # checks if button is being held down
		if (time.time() - start_time) > 2: # this was start instead of start_time before, might need to either set the timer for longer though or move the setting the start_time to just above the while loop
			GPIO.remove_event_detect(btn_increase)
			GPIO.remove_event_detect(btn_submit)
			GPIO.cleanup()
			print("Will return to the menu shortly") # the first GPIO line above until here were below the next 4 lines, which would mean I don't think would work properly because the GPIO was getting cleared *after* the setup
            off()
			setup()
			welcome()
			menu()
            return # end function here and go back to main
    
    print("Your guess: ", user_guess)

    # Compare the actual value with the user value displayed on the LEDs
	if (user_guess == answer):
		#GPIO.output(LED_value[0], False)
		#GPIO.output(LED_value[1], False)
		#GPIO.output(LED_value[2], False)
        off()
        print("Correct!")
		name = input("Enter your name: ")
        while not end_of_game:
            if len(name) < 3:
                print("Enter at least 3 characters!")
                name = input("Enter your name: ")
            else:
                name = name[0:3]
                end_of_game = True
		        save_scores()
    else:
        print("Wrong!")
        accuracy_leds()
        trigger_buzzer()
        count+=1
    # Change the PWM LED

    # if it's close enough, adjust the buzzer
    # if it's an exact guess:
    # - Disable LEDs and Buzzer
    # - tell the user and prompt them for a name
    # - fetch all the scores
    # - add the new score
    # - sort the scores
    # - Store the scores back to the EEPROM, being sure to update the score count

def off():
	GPIO.output(LED_value[0], GPIO.LOW)
	GPIO.output(LED_value[1], GPIO.LOW)
	GPIO.output(LED_value[2], GPIO.LOW)
	GPIO.output(LED_accuracy, GPIO.LOW)
	GPIO.output(buzzer, GPIO.LOW)


# LED Brightness
def accuracy_leds():

    global LED_accuracy, user_guess, answer, accuracy
    # Set the brightness of the LED based on how close the guess is to the answer
    # - The % brightness should be directly proportional to the % "closeness"
    percentage = 0

    if (user_guess < answer):
        percentage =  (user_guess)/(answer) * 100
    elif (user_guess > answer):
        percentage =  (8-user_guess)/(8-answer) * 100 # what is this formula? not proportional if you're coming from above or below from same distance. am i being dumb?

	accuracy.ChangeDutyCycle(percentage)
    # - For example if the answer is 6 and a user guesses 4, the brightness should  be at 4/6*100 = 66%
    # - If they guessed 7, the brightness would be at ((8-7)/(8-6)*100 = 50%

# Sound Buzzer
def trigger_buzzer():

    global answer, user_guess, buzzer
    # The buzzer operates differently from the LED
    # While we want the brightness of the LED to change(duty cycle), we want the frequency of the buzzer to change
    # The buzzer duty cycle should be left at 50%
    # If the user is off by an absolute value of 3, the buzzer should sound once every second
    # If the user is off by an absolute value of 2, the buzzer should sound twice every second
    # If the user is off by an absolute value of 1, the buzzer should sound 4 times a second
	if (abs(answer - user_guess) == 3):
		#buzzer = GPIO.PWM(buzzer_sound, 1)
        #buzzer.start(50)
        buzzer.ChangeFrequency(1)
	elif (abs(answer - user_guess) == 2):
		#buzzer = GPIO.PWM(buzzer_sound, 0.5)
		#buzzer.start(50)
        buzzer.ChangeFrequency(2)
	elif (abs(answer - user_guess) == 1):
		#buzzer = GPIO.PWM(buzzer_sound, 0.25)
		#buzzer(50)
        buzzer.ChangeFrequency(4)
	else:
		GPIO.output(buzzer, GPIO.LOW)

	#time.sleep(0.25)
	#GPIO.output(buzzer, GPIO.LOW)


if __name__ == "__main__":
    try:
        # Call setup function
        setup()
        welcome()
        while True:
            menu()
            pass
    except Exception as e:
        print(e)
    finally:
        GPIO.cleanup()