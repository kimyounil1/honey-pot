"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, Mail, Phone, MessageCircle } from "lucide-react"
import Link from "next/link"

export default function LoginPage() {
  const [loginMethod, setLoginMethod] = useState<"email" | "phone">("email")
  const [email, setEmail] = useState("") // 이메일 표시를 위한 state
  const [password, setPassword] = useState("") // 패스워드 표시를 위한 state
  const [error, setError] = useState("") // 에러 표시를 위한 state
  const router = useRouter()

  const handleEmailLogin = async() => {
    setError("") // 이전 에러 메세지 초기화
    if(!email){
      alert("이메일을 입력해주세요.")
      return
    }
    try{
      // const response = await fetch(`http://localhost:8000/users/by-email/${email}`)

      if (response.ok) {
        const user = await response.json()
        // 로그인 성공: 사용자 정보를 저장하고 채팅 페이지로 이동
        console.log("로그인 성공:", user)
        // TODO: (실제 앱에서는) 사용자 정보를 전역 상태나 쿠키에 저장
        router.push("/chat")
      } else if (response.status === 404) {
        // 6. 가입 되지 않은 사용자 처리
        alert("가입되지 않은 이메일입니다. 회원가입을 먼저 진행해주세요.")
      } else {
        // 기타 서버 에러
        alert("로그인 중 문제가 발생했습니다.")
      }
    } catch (err) {
      // 네트워크 에러
      console.error("Login API call error:", err)
      setError("서버와 통신할 수 없습니다.")
      }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-yellow-50 via-orange-50 to-red-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center text-gray-600 hover:text-gray-800 mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            메인으로 돌아가기
          </Link>
          <div className="flex items-center justify-center space-x-2 mb-4">
            <div className="w-10 h-10 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold">꿀</span>
            </div>
            <span className="text-2xl font-bold text-gray-800">꿀통</span>
          </div>
          <Badge variant="secondary" className="mb-4">
            내가 놓친 보험금
          </Badge>
        </div>

        <Card className="shadow-lg">
          <CardHeader className="space-y-4">
            <CardTitle className="text-center">로그인</CardTitle>
            <CardDescription className="text-center">개인정보는 최소한만 수집하며, 안전하게 보호됩니다</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">

            {/* 이메일/전화번호 로그인 */}
            <div className="space-y-4">
              <div className="space-y-3">
                <div>
                  <Label htmlFor="login-input">이메일 주소</Label>
                  <Input
                    id="login-input"
                    type="email"
                    placeholder="example@email.com"
                    className="mt-1"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}  // input 변경시 state 업데이트
                  />
                </div>
                <div>
                  <Label htmlFor="password">비밀번호</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="비밀번호"
                    className="mt-1"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
                <Button
                  className="w-full bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
                  size="lg"
                  onClick={handleEmailLogin}> 로그인
                </Button>
              </div>
            </div>

            <div className="text-center space-y-2">
              <p className="text-sm text-gray-600">
                아직 계정이 없으신가요?{" "}
                <Link href="/signup" className="text-orange-600 hover:text-orange-700 font-medium">
                  회원가입
                </Link>
              </p>
              <p className="text-xs text-gray-500">
                로그인 시{" "}
                <Link href="/terms" className="underline">
                  이용약관
                </Link>{" "}
                및{" "}
                <Link href="/privacy" className="underline">
                  개인정보처리방침
                </Link>
                에 동의합니다
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
