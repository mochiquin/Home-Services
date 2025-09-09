"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { login } from "@/lib/api"

export default function LoginPage() {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  })


  const [error, setError] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
    if (error) setError("")
  }


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()


    if (!formData.email || !formData.password) {
      setError("Please fill in all fields")
      return
    }

    setIsLoading(true)
    setError("")

    try {
      const response = await login(formData.email, formData.password)
      console.log("Login successful:", response)

      router.push("/dashboard")

    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 
                          error.response?.data?.message || 
                          error.message ||
                          "Login failed. Please check your credentials."
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Login to your account</CardTitle>
          <CardDescription>
            Enter your email below to login to your account
          </CardDescription>
          <CardAction>
            <Button variant="link">Sign Up</Button>
          </CardAction>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit}>
            <div className="flex flex-col gap-6">
              {/* wrong message */}
              {error && (
                <div className="text-destructive text-sm p-2 bg-destructive/10 rounded">
                  {error}
                </div>
              )}

              <div className="grid gap-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="m@example.com"
                  value={formData.email}
                  onChange={handleChange}
                  disabled={isLoading}
                  required
                />
              </div>

              <div className="grid gap-2">
                <div className="flex items-center">
                  <Label htmlFor="password">Password</Label>
                  <a
                    href="#"
                    className="ml-auto inline-block text-sm underline-offset-4 hover:underline"
                    onClick={(e) => e.preventDefault()}
                  >
                    Forgot your password?
                  </a>
                </div>
                <Input 
                  id="password" 
                  name="password"
                  type="password" 
                  value={formData.password}
                  onChange={handleChange}
                  disabled={isLoading}
                  required 
                />
              </div>

              {/* wrong message */}
              <Button 
                type="submit" 
                className="w-full" 
                disabled={isLoading}
              >
                {isLoading ? "Signing in..." : "Login"}
              </Button>
            </div>
          </form>
        </CardContent>

        <CardFooter className="flex-col gap-2">
          <Button variant="outline" className="w-full" disabled={isLoading}>
            Login with Google
          </Button>
        </CardFooter>
      </Card>
    </div>
  )
}