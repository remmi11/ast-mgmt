from django import template

register = template.Library()

def get_value(value, arg):
	return value[arg]

def multiply(value, arg):
	return value * arg

register.filter('get_value', get_value)
register.filter('multiply', multiply)