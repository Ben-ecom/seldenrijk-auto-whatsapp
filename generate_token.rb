user = User.first || User.create!(
  email: 'admin@seldenrijk.nl',
  password: 'SecurePass123!',
  name: 'Seldenrijk Admin',
  confirmed_at: Time.now
)

puts "User ID: #{user.id}"
puts "User Email: #{user.email}"

key = user.access_token || user.create_access_token
puts "API Token: #{key.token}"
