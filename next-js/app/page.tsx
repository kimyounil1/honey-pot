"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { MessageCircle, TrendingUp, Shield, Users, ArrowRight, Star, Menu, X, Droplet } from 'lucide-react' // Coffee 대신 Droplet 아이콘 사용
import Link from "next/link"
import Image from "next/image" // Image 컴포넌트 임포트

export default function HomePage() {
const [hoveredCard, setHoveredCard] = useState<number | null>(null)
const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
const [isLoggedIn, setIsLoggedIn] = useState(false) // 로그인 상태 추가

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
color: "bg-orange-50 text-orange-600",
},
{
icon: TrendingUp,
title: "내가 모르는 보험금 받기",
description: "놓치고 있던 환급금과 보장 혜택을 찾아드려요",
color: "bg-yellow-50 text-yellow-600",
},
{
icon: Shield,
title: "보험사가 숨기는 환급금",
description: "보험사들이 알려주지 않는 숨겨진 혜택을 공개해요",
color: "bg-red-50 text-red-600",
},
]

const navItems = [
{ name: "채팅하기", href: "/chat" },
{ name: "보험 약관 분석", href: "/analysis" },
{ name: "환급금 찾기", href: "/refund" },
{ name: "보험 분석", href: "/insurance-analysis" },
]

return (
<div className="min-h-screen bg-white">
{/* Header */}
<header className="relative z-50 bg-white/95 backdrop-blur-sm border-b border-gray-100">
<div className="container mx-auto px-4 py-4">
<div className="flex items-center justify-between">
  {/* Logo */}
  <Link href="/" className="flex items-center space-x-3">
    <div className="w-10 h-10 bg-gradient-to-r from-orange-400 to-orange-500 rounded-xl flex items-center justify-center shadow-lg">
      <Droplet className="h-5 w-5 text-white" /> {/* Droplet 아이콘으로 변경 */}
    </div>
    <span className="text-base font-bold text-gray-800">꿀통</span> {/* 글씨 크기 0.5배로 축소 */}
  </Link>

  {/* Desktop Navigation */}
  <nav className="hidden md:flex items-center space-x-8">
    {navItems.map((item, index) => (
      <Link
        key={index}
        href={isLoggedIn ? item.href : '/login'} // 로그인 상태에 따라 링크 변경
        className="text-gray-600 hover:text-orange-500 transition-colors font-medium"
      >
        {item.name}
      </Link>
    ))}
  </nav>

  {/* Desktop CTA */}
  <div className="hidden md:flex items-center space-x-4">
    <Link href="/login">
      <Button className="bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 text-white font-semibold px-6 py-2 rounded-full shadow-lg hover:shadow-xl transition-all duration-300">
        로그인 하기
      </Button>
    </Link>
  </div>

  {/* Mobile Menu Button */}
  <Button
    variant="ghost"
    size="sm"
    className="md:hidden"
    onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
  >
    {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
  </Button>
</div>

{/* Mobile Menu */}
{mobileMenuOpen && (
  <div className="md:hidden mt-4 pb-4 border-t border-gray-100">
    <nav className="flex flex-col space-y-4 mt-4">
      {navItems.map((item, index) => (
        <Link
          key={index}
          href={isLoggedIn ? item.href : '/login'} // 로그인 상태에 따라 링크 변경
          className="text-gray-600 hover:text-orange-500 transition-colors font-medium"
          onClick={() => setMobileMenuOpen(false)}
        >
          {item.name}
        </Link>
      ))}
      <Link href="/login" onClick={() => setMobileMenuOpen(false)}>
        <Button className="w-full bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 text-white font-semibold rounded-full shadow-lg">
          로그인 하기
        </Button>
      </Link>
    </nav>
  </div>
)}
</div>
</header>

{/* Hero Section - 시그널플래너 스타일로 심플하게 */}
<section className="relative min-h-screen flex items-center justify-center overflow-hidden">
{/* Background - 옅은 주황색 그라데이션 */}
<div className="absolute inset-0 z-0 bg-gradient-to-br from-orange-100 via-orange-200 to-yellow-100">
</div>

{/* Content - 매우 심플하게 */}
<div className="relative z-10 text-center text-gray-800 px-4 max-w-6xl mx-auto">
{/* 메인 타이틀 */}
<h1 className="text-5xl md:text-6xl lg:text-7xl font-bold mb-12 leading-tight tracking-tight">
  보험금도 꿀처럼 쉽게
</h1>

{/* CTA 버튼 - 중앙에 하나만 */}
<div className="flex justify-center">
  <Link href="/login"> {/* 항상 로그인 페이지로 이동 */}
    <Button
      size="lg"
      className="bg-gradient-to-r from-orange-400 to-orange-500 hover:from-orange-500 hover:to-orange-600 text-white font-bold text-xl px-12 py-6 rounded-full shadow-2xl hover:shadow-3xl transform hover:scale-105 transition-all duration-300"
    >
      로그인하고 환급금 찾기 {/* 텍스트 변경 */}
    </Button>
  </Link>
</div>
</div>

{/* Scroll Indicator */}
<div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 animate-bounce">
<div className="w-6 h-10 border-2 border-gray-600 rounded-full flex justify-center">
  <div className="w-1 h-3 bg-gray-600 rounded-full mt-2 animate-pulse"></div>
</div>
</div>
</section>

{/* Second Section: 채팅하면서 쉽게 내 보험에 대해서 알아보자 */}
<section className="py-20 bg-white">
<div className="container mx-auto px-4">
<div className="flex flex-col md:flex-row md:items-start items-center justify-between gap-12 max-w-6xl mx-auto">
  {/* Text Content - Left Aligned */}
  <div className="flex-1 text-center md:text-left">
    <h2 className="text-xl md:text-2xl font-bold text-orange-500 mb-4">꿀통 채팅하기</h2>
    <p className="text-2xl md:text-3xl font-semibold text-gray-800 leading-relaxed">
      채팅하면서 쉽게
      <br />
      내 보험에 대해서 알아보자
    </p>
  </div>
  {/* Image Placeholder - Right Side */}
  <div className="flex-1 flex justify-center md:justify-end">
    <Image
      src="/placeholder.svg?height=300&width=300"
      alt="Chatting about insurance"
      width={300}
      height={300}
      className="rounded-lg shadow-xl"
    />
  </div>
</div>
</div>
</section>

{/* Third Section: 내 보험이나 내가 알고 싶은 보험사의 보험 약관 분석 받고 요약 받자 */}
<section className="py-20 bg-gray-50">
<div className="container mx-auto px-4">
<div className="flex flex-col md:flex-row-reverse md:items-start items-center justify-between gap-12 max-w-6xl mx-auto">
  {/* Text Content - Right Aligned */}
  <div className="flex-1 text-center md:text-right">
    <h2 className="text-xl md:text-2xl font-bold text-orange-500 mb-4">꿀통 보험 약관 분석</h2>
    <p className="text-2xl md:text-3xl font-semibold text-gray-800 leading-relaxed">
      내 보험이나 내가 알고 싶은 보험사의
      <br />
      보험 약관 분석 받고 요약 받자
    </p>
  </div>
  {/* Image Placeholder - Left Side */}
  <div className="flex-1 flex justify-center md:justify-start">
    <Image
      src="/placeholder.svg?height=300&width=300"
      alt="Document analysis"
      width={300}
      height={300}
      className="rounded-lg shadow-xl"
    />
  </div>
</div>
</div>
</section>

{/* Fourth Section: 내가 몰라서 못받은 환급금과 이미 놓친 환급금들 찾아서 받자 */}
<section className="py-20 bg-white">
<div className="container mx-auto px-4">
<div className="flex flex-col md:flex-row md:items-start items-center justify-between gap-12 max-w-6xl mx-auto">
  {/* Text Content - Left Aligned */}
  <div className="flex-1 text-center md:text-left">
    <h2 className="text-xl md:text-2xl font-bold text-orange-500 mb-4">꿀통 환급금 찾기</h2>
    <p className="text-2xl md:text-3xl font-semibold text-gray-800 leading-relaxed">
      내가 몰라서 못받은 환급금과
      <br />
      이미 놓친 환급금들 찾아서 받자
    </p>
  </div>
  {/* Image Placeholder - Right Side */}
  <div className="flex-1 flex justify-center md:justify-end">
    <Image
      src="/placeholder.svg?height=300&width=300"
      alt="Finding insurance refunds"
      width={300}
      height={300}
      className="rounded-lg shadow-xl"
    />
  </div>
</div>
</div>
</section>

{/* Fifth Section: 내 보험은 어떨까? (통합 섹션) */}
<section className="py-20 bg-gray-50">
<div className="container mx-auto px-4">
<div className="flex flex-col md:flex-row-reverse md:items-start items-center justify-between gap-12 max-w-6xl mx-auto">
  {/* Text Content - Right Aligned */}
  <div className="flex-1 text-center md:text-right">
    <h2 className="text-xl md:text-2xl font-bold text-orange-500 mb-4">꿀통 보험 분석</h2>
    <p className="text-2xl md:text-3xl font-semibold text-gray-800 leading-relaxed">
      내 보험은 어떨까?
      <br />
      보험금을 줄이고
      <br />
      더 좋은 보장이 있는지 분석 해보자
    </p>
  </div>
  {/* Image Placeholder - Left Side */}
  <div className="flex-1 flex justify-center md:justify-start">
    <Image
      src="/placeholder.svg?height=300&width=300"
      alt="Insurance assessment and cost reduction analysis"
      width={300}
      height={300}
      className="rounded-lg shadow-xl"
    />
  </div>
</div>
</div>
</section>

{/* New Section: 보험사들도 절대 안알려준다 */}
<section className="py-20 bg-gradient-to-br from-orange-50 to-yellow-50">
<div className="container mx-auto px-4 text-center">
<h2 className="text-4xl md:text-5xl font-bold text-orange-500 mb-4">보험사들도 절대 안알려줘요!</h2>
<p className="text-3xl md:text-4xl font-bold text-gray-800 max-w-3xl mx-auto mb-12 leading-relaxed">
  꿀통이 숨어 있는 보장까지 전부 다<br />찾아드리고, 알려 드릴게요!
</p>
<div className="flex flex-col md:flex-row justify-center items-center gap-8 max-w-6xl mx-auto">
  <Image
    src="/placeholder.svg?height=250&width=350"
    alt="Insurance policy example"
    width={350}
    height={250}
    className="rounded-lg shadow-xl"
  />
  <Image
    src="/placeholder.svg?height=250&width=350"
    alt="Financial analysis example"
    width={350}
    height={250}
    className="rounded-lg shadow-xl"
  />
  <Image
    src="/placeholder.svg?height=250&width=350"
    alt="Refund example"
    width={350}
    height={250}
    className="rounded-lg shadow-xl"
  />
</div>
</div>
</section>

{/* Testimonials Section */}
<section className="py-20 bg-white">
<div className="container mx-auto px-4">
<div className="text-center mb-16">
  <h2 className="text-4xl font-bold text-orange-500 mb-4">실제 회원들의 환급금 받은 후기</h2>
  <p className="text-xl text-gray-600">꿀통과 함께한 회원들의 생생한 경험담을 확인해보세요!</p>
</div>
<div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
  {testimonials.map((testimonial, index) => (
    <Card key={index} className="hover:shadow-2xl transition-all duration-300 border-0 shadow-lg">
      <CardHeader>
        <div className="flex items-center space-x-4">
          <Avatar className="w-12 h-12">
            <AvatarImage src={testimonial.avatar || "/placeholder.svg"} />
            <AvatarFallback className="bg-orange-100 text-orange-600 font-bold">
              {testimonial.name[0]}
            </AvatarFallback>
          </Avatar>
          <div>
            <h4 className="font-bold text-lg">
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
          <div className="text-3xl font-bold text-orange-500 mb-4">+{testimonial.amount}</div>
          <p className="text-gray-600 leading-relaxed">"{testimonial.review}"</p>
        </CardContent>
      </Card>
    ))}
  </div>
</div>
</section>

{/* CTA Section */}
<section className="py-20 bg-white">
  <div className="container mx-auto px-4 text-center">
    <div className="max-w-4xl mx-auto text-gray-800">
      <h2 className="text-4xl font-bold mb-6">
        꿀통과 채팅으로 더 나은 보장 받은 회원 수<br />
        <span className="text-orange-500 font-bold text-7xl">2,103,402</span>
        <span className="text-gray-800 font-bold text-6xl">건</span>
      </h2>
      <p className="text-2xl mb-12 leading-relaxed">
        꿀통과 채팅 후 더이상 환급금 놓치지 마세요!
      </p>
    </div>
  </div>
</section>

{/* Footer */}
<footer className="bg-white text-gray-700 py-12">
  <div className="container mx-auto px-4 text-left max-w-6xl">
    <div className="flex items-center space-x-3 mb-6">
      <Image
        src="/placeholder.svg?height=40&width=40"
        alt="꿀통 Logo"
        width={40}
        height={40}
        className="rounded-lg"
      />
      <span className="text-2xl font-bold text-gray-800">꿀통</span>
    </div>
    <div className="text-sm space-y-1 mb-6">
      <p>(주)꿀통 | 서울특별시 강남구 역삼로25길 36</p>
      <p>
        대표자 : 홍길동 | 사업자등록번호 : 123-45-67890 [사업자정보확인] | 통신판매업신고 : 2025-서울강남-00000
      </p>
    </div>
    <div className="text-sm space-y-1 mb-8">
      <p>개인정보담당자 : privacy@kkultong.co | 제휴문의 : hello@kkultong.co</p>
      <p>고객만족센터 : help@kkultong.co | 대표전화 : 02-1234-5678</p>
    </div>
    <div className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-gray-500">
      <p>© 2025 꿀통</p>
      <Link href="/terms" className="hover:underline">
        이용약관
      </Link>
      <Link href="/paid-terms" className="hover:underline">
        유료서비스 이용약관
      </Link>
      <Link href="/privacy" className="text-blue-600 hover:underline">
        개인정보처리방침
      </Link>
      <Link href="/consumer-protection" className="hover:underline">
        소비자보호
      </Link>
    </div>
  </div>
</footer>
</div>
)
}
