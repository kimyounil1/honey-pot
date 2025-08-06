"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Checkbox } from "@/components/ui/checkbox"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, MessageCircle, Shield, Clock } from "lucide-react"
import Link from "next/link"

export default function SignupPage() {
  const [signupMethod, setSignupMethod] = useState<"social" | "email" | "phone">("social")
  const [agreements, setAgreements] = useState({
    terms: false,
    privacy: false,
    marketing: false,
  })
  const [email, setEmail] = useState("")
  const [name, setName] = useState("")
  const [password, setPassword] = useState("")
  const [birthDate, setBirthDate] = useState("")

  const handleSignup = async () => {
    if (!agreements.terms || !agreements.privacy) {
      alert("필수 약관에 동의해주세요.")
      return
    }

    // 생년월일 형식 변환 (YYMMDD -> YYYY-MM-DD)
    const year = parseInt(birthDate.substring(0, 2), 10)
    const month = birthDate.substring(2, 4)
    const day = birthDate.substring(4, 6)
    const fullYear = year < 50 ? 2000 + year : 1900 + year // 2000년생 이후와 이전 구분
    const formattedBirthDate = `${fullYear}-${month}-${day}`

    try {
      const response = await fetch("http://localhost:8000/users/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name: name,
          email: email,
          password: password,
          birth_date: formattedBirthDate,
        }),
      })

      if (response.ok) {
        alert("회원가입이 완료되었습니다!")
        // 로그인 페이지로 리디렉션 또는 다른 작업 수행
        window.location.href = "/login"
      } else {
        const errorData = await response.json()
        alert(`회원가입 실패: ${errorData.detail || "알 수 없는 오류"}`)
      }
    } catch (error) {
      console.error("회원가입 중 오류 발생:", error)
      alert("회원가입 중 오류가 발생했습니다.")
    }
  }

  const benefits = [
    {
      icon: Shield,
      title: "개인 맞춤 보험 분석",
      description: "나만의 보험 포트폴리오 관리",
    },
    {
      icon: Clock,
      title: "24시간 상담 이력 저장",
      description: "언제든 이전 상담 내용 확인",
    },
    {
      icon: MessageCircle,
      title: "우선 상담 서비스",
      description: "회원 전용 빠른 응답",
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-yellow-50 via-orange-50 to-red-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <Link href="/login" className="inline-flex items-center text-gray-600 hover:text-gray-800 mb-4">
            <ArrowLeft className="h-4 w-4 mr-2" />
            로그인으로 돌아가기
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
          {/* <h1 className="text-2xl font-bold text-gray-800 mb-2">간편 회원가입</h1>
          <p className="text-gray-600">3초만에 가입하고 더 많은 혜택을 받아보세요</p> */}
        </div>

        {/* Benefits */}
        <Card className="mb-6 bg-gradient-to-r from-yellow-50 to-orange-50 border-yellow-200">
          <CardHeader>
            <CardTitle className="text-center text-lg">회원 전용 혜택</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {benefits.map((benefit, index) => (
                <div key={index} className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-full flex items-center justify-center">
                    <benefit.icon className="h-4 w-4 text-white" />
                  </div>
                  <div>
                    <h4 className="font-medium text-sm">{benefit.title}</h4>
                    <p className="text-xs text-gray-600">{benefit.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-lg">
          <CardHeader>
            <CardTitle className="text-center">이메일로 회원가입</CardTitle>
            <CardDescription className="text-center">개인정보는 최소한만 수집하며, 안전하게 보호됩니다</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* 소셜 회원가입 */}
            {signupMethod === "social" && (
              <div className="space-y-3">
                {/* <Button className="w-full bg-yellow-400 hover:bg-yellow-500 text-gray-800 font-medium" size="lg">
                  <MessageCircle className="mr-2 h-5 w-5" />
                  카카오로 3초만에 가입하기
                </Button>

                <Button
                  variant="outline"
                  className="w-full border-green-500 text-green-600 hover:bg-green-50 bg-transparent"
                  size="lg"
                >
                  <span className="mr-2 text-lg font-bold">N</span>
                  네이버로 가입하기
                </Button> */}

                <div className="text-center">
                  <Button variant="ghost" size="sm" onClick={() => setSignupMethod("email")}>
                    가입하기
                  </Button>
                </div>
              </div>
            )}

            {/* 이메일 회원가입 */}
            {signupMethod === "email" && (
              <div className="space-y-4">
                <div className="space-y-3">
                  <div>
                    <Label htmlFor="email">이메일 주소</Label>
                    <Input
                      id="email"
                      type="email"
                      placeholder="example@email.com"
                      className="mt-1"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="name">이름</Label>
                    <Input
                      id="name"
                      type="text"
                      placeholder="홍길동"
                      className="mt-1"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
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
                  <div>
                    <Label htmlFor="birth_date">생년월일(주민번호 앞자리)</Label>
                    <Input
                      id="birth_date"
                      type="text"
                      placeholder="예) 920418"
                      className="mt-1"
                      value={birthDate}
                      onChange={(e) => setBirthDate(e.target.value)}
                    />
                  </div>
                </div>

                <Button
                  className="w-full bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
                  size="lg"
                  onClick={handleSignup}
                >
                  가입하기
                </Button>

                {/* <div className="text-center">
                  <Button variant="ghost" size="sm" onClick={() => setSignupMethod("social")}>
                    소셜 로그인으로 돌아가기
                  </Button>
                </div> */}
              </div>
            )}

            {/* 약관 동의 */}
            <div className="space-y-3">
              <Separator />
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="terms"
                    checked={agreements.terms}
                    onCheckedChange={(checked) => setAgreements((prev) => ({ ...prev, terms: checked as boolean }))}
                  />
                  <Label htmlFor="terms" className="text-sm">
                    <span className="text-red-500">*</span> 이용약관에 동의합니다
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="privacy"
                    checked={agreements.privacy}
                    onCheckedChange={(checked) => setAgreements((prev) => ({ ...prev, privacy: checked as boolean }))}
                  />
                  <Label htmlFor="privacy" className="text-sm">
                    <span className="text-red-500">*</span> 개인정보처리방침에 동의합니다
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="marketing"
                    checked={agreements.marketing}
                    onCheckedChange={(checked) => setAgreements((prev) => ({ ...prev, marketing: checked as boolean }))}
                  />
                  <Label htmlFor="marketing" className="text-sm">
                    마케팅 정보 수신에 동의합니다 (선택)
                  </Label>
                </div>
              </div>
            </div>

            <div className="text-center">
              <p className="text-sm text-gray-600">
                이미 계정이 있으신가요?{" "}
                <Link href="/login" className="text-orange-600 hover:text-orange-700 font-medium">
                  로그인
                </Link>
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
