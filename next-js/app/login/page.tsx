"use client"

import { useState } from "react"
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
          <h1 className="text-2xl font-bold text-gray-800 mb-2">간편 로그인</h1>
          <p className="text-gray-600">빠르고 안전하게 시작하세요</p>
        </div>

        <Card className="shadow-lg">
          <CardHeader className="space-y-4">
            <CardTitle className="text-center">로그인 방법 선택</CardTitle>
            <CardDescription className="text-center">개인정보는 최소한만 수집하며, 안전하게 보호됩니다</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* 소셜 로그인 */}
            <div className="space-y-3">
              <Button className="w-full bg-yellow-400 hover:bg-yellow-500 text-gray-800 font-medium" size="lg">
                <MessageCircle className="mr-2 h-5 w-5" />
                카카오로 3초만에 시작하기
              </Button>

              <Button
                variant="outline"
                className="w-full border-green-500 text-green-600 hover:bg-green-50 bg-transparent"
                size="lg"
              >
                <span className="mr-2 text-lg font-bold">N</span>
                네이버로 시작하기
              </Button>
            </div>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <Separator />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-white px-2 text-gray-500">또는</span>
              </div>
            </div>

            {/* 이메일/전화번호 로그인 */}
            <div className="space-y-4">
              <div className="flex space-x-2">
                <Button
                  variant={loginMethod === "email" ? "default" : "outline"}
                  className="flex-1"
                  onClick={() => setLoginMethod("email")}
                >
                  <Mail className="mr-2 h-4 w-4" />
                  이메일
                </Button>
                <Button
                  variant={loginMethod === "phone" ? "default" : "outline"}
                  className="flex-1"
                  onClick={() => setLoginMethod("phone")}
                >
                  <Phone className="mr-2 h-4 w-4" />
                  휴대폰
                </Button>
              </div>

              <div className="space-y-3">
                <div>
                  <Label htmlFor="login-input">{loginMethod === "email" ? "이메일 주소" : "휴대폰 번호"}</Label>
                  <Input
                    id="login-input"
                    type={loginMethod === "email" ? "email" : "tel"}
                    placeholder={loginMethod === "email" ? "example@email.com" : "010-1234-5678"}
                    className="mt-1"
                  />
                </div>

                <Button
                  className="w-full bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600"
                  size="lg"
                >
                  {loginMethod === "email" ? "이메일로 로그인" : "인증번호 받기"}
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

        {/* 게스트 이용 안내 */}
        <Card className="mt-6 bg-blue-50 border-blue-200">
          <CardContent className="pt-6">
            <div className="text-center">
              <h3 className="font-medium text-blue-800 mb-2">로그인 없이도 이용 가능!</h3>
              <p className="text-sm text-blue-600 mb-4">기본적인 보험 상담은 회원가입 없이도 바로 시작할 수 있어요</p>
              <Link href="/chat">
                <Button variant="outline" className="border-blue-300 text-blue-600 hover:bg-blue-100 bg-transparent">
                  게스트로 체험해보기
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
