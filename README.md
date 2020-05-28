# Project 1

1. Register 
   - used `check_password_hash, generate_password_hash` from `werkzeug.security ` to hash the password
   - check duplicate username
   - password must be longer than 6 characters.
   - check if passwords match
   - redirect to login page after the register
2. Login 
   - same as register 
   - redirect to search
3. search
   - search the book 
   - list the result 
   - search isbn, title, author at the same time
4. book
	- two columns 
	- book info rendered with card component
	- book cover image from another api 
	- goodread review score at the bottom of the title card
	- review score rendered with stars
	- user can review the book with stars
	- can post a review 
	- once a review posted, the page reload with the new review on top
5. API Access
	- as per the project description
