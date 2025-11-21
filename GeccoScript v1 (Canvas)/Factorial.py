# factorial example
def fact(n)
  if n <= 1
    return 1
  end
  return n * fact(n - 1)
end

n = 6
print "n ="
print n
print "fact(n) ="
print fact(n)