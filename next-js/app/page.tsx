"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { MessageCircle, TrendingUp, Shield, Users, ArrowRight, Star } from "lucide-react"
import Link from "next/link"

export default function HomePage() {
  const [hoveredCard, setHoveredCard] = useState<number | null>(null)

  const testimonials = [
    {
      name: "김민수",
      age: 34,
      amount: "2,340,000원",
      review: "10년간 몰랐던 실손보험 환급금을 찾았어요! 꿀통 덕분에 놓친 돈을 되찾았습니다.",
      avatar: "/placeholder.svg?height=40&width=40",
    },
    {
      name: "박지영",
      age: 28,
      amount: "1,850,000원",
      review: "보험설계사도 알려주지 않은 특약 환급금까지! 정말 꼼꼼하게 분석해주세요.",
      avatar: "/placeholder.svg?height=40&width=40",
    },
    {
      name: "이준호",
      age: 42,
      amount: "3,120,000원",
      review: "복잡한 보험 약관을 AI가 쉽게 설명해줘서 이해하기 쉬웠어요.",
      avatar: "/placeholder.svg?height=40&width=40",
    },
  ]

  const features = [
    {
      icon: MessageCircle,
      title: "내 보험 제대로 알기",
      description: "복잡한 보험 약관을 AI가 쉽게 설명해드려요",
      color: "bg-blue-50 text-blue-600",
    },
    {
      icon: TrendingUp,
      title: "내가 모르는 보험금 받기",
      description: "놓치고 있던 환급금과 보장 혜택을 찾아드려요",
      color: "bg-green-50 text-green-600",
    },
    {
      icon: Shield,
      title: "보험사가 숨기는 환급금",
      description: "보험사들이 알려주지 않는 숨겨진 혜택을 공개해요",
      color: "bg-orange-50 text-orange-600",
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-yellow-50 via-orange-50 to-red-50">
      {/* Header */}
      <header className="border-b bg-white/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-r from-yellow-400 to-orange-500 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">꿀</span>
            </div>
            <span className="text-xl font-bold text-gray-800">꿀통</span>
            <Badge variant="secondary" className="ml-2">
              내가 놓친 보험금
            </Badge>
          </div>
          <div className="flex items-center space-x-4">
            <Link href="/login">
              <Button variant="outline">로그인</Button>
            </Link>
            <Link href="/chat">
              <Button className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600">
                무료로 시작하기
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-16 text-center">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-5xl font-bold text-gray-800 mb-6 leading-tight">
            아무도 내 보험 환급금에 대해서
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-yellow-500 to-orange-500">
              자세히 알려주지 않는다
            </span>
          </h1>
          <p className="text-xl text-gray-600 mb-8 leading-relaxed">
            보험사들이 싫어하는 꿀통과 함께하면
            <br />
            당신의 간지러운 곳을 긁어드릴게요
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
            <Link href="/chat">
              <Button
                size="lg"
                className="bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-lg px-8 py-4"
              >
                <MessageCircle className="mr-2 h-5 w-5" />
                지금 바로 환급금 찾기
                <ArrowRight className="ml-2 h-5 w-5" />
              </Button>
            </Link>
            <p className="text-sm text-gray-500">로그인 없이도 바로 시작 가능</p>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-16">
        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {features.map((feature, index) => (
            <Card
              key={index}
              className={`cursor-pointer transition-all duration-300 hover:shadow-lg hover:-translate-y-1 ${
                hoveredCard === index ? "ring-2 ring-yellow-400" : ""
              }`}
              onMouseEnter={() => setHoveredCard(index)}
              onMouseLeave={() => setHoveredCard(null)}
            >
              <CardHeader className="text-center">
                <div
                  className={`w-16 h-16 rounded-full ${feature.color} flex items-center justify-center mx-auto mb-4`}
                >
                  <feature.icon className="h-8 w-8" />
                </div>
                <CardTitle className="text-xl">{feature.title}</CardTitle>
                <CardDescription className="text-base">{feature.description}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="bg-white py-16">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-800 mb-4">실제 회원들의 환급금 받은 후기</h2>
            <p className="text-gray-600">꿀통과 함께한 회원들의 생생한 경험담을 확인해보세요</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {testimonials.map((testimonial, index) => (
              <Card key={index} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-center space-x-4">
                    <Avatar>
                      <AvatarImage src={testimonial.avatar || "/placeholder.svg"} />
                      <AvatarFallback>{testimonial.name[0]}</AvatarFallback>
                    </Avatar>
                    <div>
                      <h4 className="font-semibold">
                        {testimonial.name} ({testimonial.age}세)
                      </h4>
                      <div className="flex items-center">
                        {[...Array(5)].map((_, i) => (
                          <Star key={i} className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                        ))}
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold text-green-600 mb-3">+{testimonial.amount}</div>
                  <p className="text-gray-600 text-sm leading-relaxed">"{testimonial.review}"</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-gradient-to-r from-yellow-500 to-orange-500 py-16">
        <div className="container mx-auto px-4 text-center">
          <div className="max-w-3xl mx-auto text-white">
            <h2 className="text-3xl font-bold mb-4">내 보험 설계사를 믿지 마라</h2>
            <p className="text-xl mb-8 opacity-90">지금 바로 꿀통과 함께 놓친 보험금을 찾아보세요</p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/chat">
                <Button size="lg" variant="secondary" className="text-lg px-8 py-4">
                  <Users className="mr-2 h-5 w-5" />
                  무료 상담 시작하기
                </Button>
              </Link>
              <Link href="/login">
                <Button
                  size="lg"
                  variant="outline"
                  className="text-lg px-8 py-4 bg-transparent border-white text-white hover:bg-white hover:text-orange-500"
                >
                  회원가입하고 더 많은 혜택 받기
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-800 text-white py-8">
        <div className="container mx-auto px-4 text-center">
          <div className="flex items-center justify-center space-x-2 mb-4">
            <div className="w-6 h-6 bg-gradient-to-r from-yellow-400 to-orange-500 rounded flex items-center justify-center">
              <span className="text-white font-bold text-xs">꿀</span>
            </div>
            <span className="text-lg font-bold">꿀통</span>
          </div>
          <p className="text-gray-400 text-sm">© 2025 꿀통. 내가 놓친 보험금 찾기 서비스</p>
        </div>
      </footer>
    </div>
  )
}
